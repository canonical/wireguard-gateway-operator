# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

import ipaddress

import pytest

import wgdb
from tests.unit.helpers import example_private_key, example_public_key
from wgdb import _WIREGUARD_PORT_RANGE, WireguardDb, WireguardLinkStatus


@pytest.fixture
def db(tmp_path):
    return WireguardDb(tmp_path / "wg.json")


def test_init(tmp_path):
    db_file = tmp_path / "wg.json"
    db = WireguardDb(db_file)
    assert db_file.exists()
    assert db._data.port_counter == _WIREGUARD_PORT_RANGE[0]


def test_allocate_port(db):
    port1 = db.allocate_port(is_provider=True)
    assert port1 % 2 == 1
    assert port1 >= _WIREGUARD_PORT_RANGE[0]

    port2 = db.allocate_port(is_provider=False)
    assert port2 % 2 == 0
    assert port2 >= _WIREGUARD_PORT_RANGE[0]

    port3 = db.allocate_port(is_provider=True)
    assert port3 % 2 == 1
    assert port3 != port1


def test_key_management(db):
    public_key = example_public_key("wg", 1)
    private_key = example_private_key("wg", 1)
    owner = 123

    db.add_key(owner=owner, public_key=public_key, private_key=private_key)

    keys = db.list_keys()
    assert len(keys) == 1
    assert keys[0].public_key == public_key
    assert keys[0].private_key == private_key
    assert keys[0].owner == owner
    assert not keys[0].retired

    k = db.search_key(public_key)
    assert k is not None
    assert k.public_key == public_key

    db.retire_key(public_key)
    keys_active = db.list_keys()
    assert len(keys_active) == 0

    keys_all = db.list_keys(include_retired=True)
    assert len(keys_all) == 1
    assert keys_all[0].retired
    assert keys_all[0].retired_at is not None

    db.remove_key(public_key)
    assert len(db.list_keys(include_retired=True)) == 0


def test_key_not_found_on_retire(db):
    with pytest.raises(KeyError, match="public key not found"):
        db.retire_key(example_public_key("wg", 1))


def test_link_lifecycle(db):
    owner = 100
    local_public_key = example_public_key("wg", 1)
    local_private_key = example_private_key("wg", 1)
    peer_public_key = example_public_key("wg", 2)
    port = 50000
    allowed_ips = [ipaddress.ip_network("192.168.1.0/24")]

    db.add_key(owner=owner, public_key=local_public_key, private_key=local_private_key)

    db.open_link(
        owner=owner,
        public_key=local_public_key,
        port=port,
        peer_public_key=peer_public_key,
        allowed_ips=allowed_ips,
    )

    link = db.search_link(local_public_key, peer_public_key)
    assert link is not None
    assert link.status == WireguardLinkStatus.HALF_OPEN
    assert link.peer_endpoint is None
    assert len(link.peer_allowed_ips) == 1
    assert isinstance(link.peer_allowed_ips[0], (ipaddress.IPv4Network, ipaddress.IPv6Network))

    endpoint = "10.0.0.1:51820"
    db.acknowledge_open_link(local_public_key, peer_public_key, endpoint)

    link = db.search_link(local_public_key, peer_public_key)
    assert link.status == WireguardLinkStatus.OPEN
    assert link.peer_endpoint == endpoint

    new_allowed = [ipaddress.ip_network("10.10.10.0/24")]
    db.update_link(local_public_key, peer_public_key, peer_allowed_ips=new_allowed)
    link = db.search_link(local_public_key, peer_public_key)
    assert str(link.peer_allowed_ips[0]) == "10.10.10.0/24"

    db.close_link(local_public_key, peer_public_key)
    link = db.search_link(local_public_key, peer_public_key)
    assert link.status == WireguardLinkStatus.HALF_CLOSE
    assert link.closed_at is not None

    db.acknowledge_close_link(local_public_key, peer_public_key)
    link = db.search_link(local_public_key, peer_public_key)
    assert link.status == WireguardLinkStatus.CLOSE

    assert len(db.list_link(include_closed=False)) == 0
    assert len(db.list_link(include_closed=True)) == 1

    db.remove_link(local_public_key, peer_public_key)
    assert len(db.list_link(include_closed=True)) == 0


def test_open_link_missing_key(db):
    with pytest.raises(KeyError, match="public key not found"):
        db.open_link(
            owner=1,
            public_key=example_public_key("wg", 1),
            port=50000,
            peer_public_key=example_public_key("wg", 2),
            allowed_ips=[],
        )


def test_update_link_errors(db):
    owner = 100
    public_key = example_public_key("wg", 1)
    private_key = example_private_key("wg", 1)
    db.add_key(owner=owner, public_key=public_key, private_key=private_key)
    db.open_link(
        owner=owner,
        public_key=public_key,
        port=50000,
        peer_public_key=example_public_key("wg", 2),
        allowed_ips=[],
    )

    with pytest.raises(ValueError, match="cannot set peer_endpoint on half-open link"):
        db.update_link(public_key, example_public_key("wg", 2), peer_endpoint="1.2.3.4:5678")


def test_list_owners(db):
    db.add_key(
        owner=1,
        public_key=example_public_key("wg", 1),
        private_key=example_private_key("wg", 1),
    )

    db.add_key(
        owner=2,
        public_key=example_public_key("wg", 2),
        private_key=example_private_key("wg", 2),
    )
    db.retire_key(example_public_key("wg", 2))

    db.add_key(
        owner=3,
        public_key=example_public_key("wg", 3),
        private_key=example_private_key("wg", 3),
    )
    db.open_link(
        owner=3,
        public_key=example_public_key("wg", 3),
        port=50002,
        peer_public_key=example_public_key("wg", 4),
        allowed_ips=[],
    )

    owners = db.list_owners()
    assert 1 in owners
    assert 2 not in owners
    assert 3 in owners


def test_validate_peer_allowed_ips_objects(db):
    owner = 1
    public_key = example_public_key("wg", 1)
    private_key = example_private_key("wg", 1)
    db.add_key(owner=owner, public_key=public_key, private_key=private_key)

    net = ipaddress.ip_network("10.0.0.0/24")
    db.open_link(
        owner=owner,
        public_key=public_key,
        port=50000,
        peer_public_key=example_public_key("wg", 2),
        allowed_ips=[net],
    )

    link = db.search_link(public_key, example_public_key("wg", 2))
    assert link.peer_allowed_ips[0] == net


def test_interface_name_property(db):
    owner = 1
    public_key = example_public_key("wg", 1)
    private_key = example_private_key("wg", 1)
    db.add_key(owner=owner, public_key=public_key, private_key=private_key)
    db.open_link(
        owner=owner,
        public_key=public_key,
        port=50000,
        peer_public_key=example_public_key("wg", 2),
        allowed_ips=[],
    )

    link = db.search_link(public_key, example_public_key("wg", 2))
    assert link.interface_name == "wg50000"


def test_allocate_port_wraparound(db, monkeypatch):
    monkeypatch.setattr(wgdb, "_WIREGUARD_PORT_RANGE", (50000, 50004))

    p1 = db.allocate_port(is_provider=True)
    assert p1 == 50001

    from wgdb import WireguardLink, WireguardLinkStatus

    db._data.links.append(
        WireguardLink(
            owner=1,
            status=WireguardLinkStatus.OPEN,
            public_key=example_public_key("wg", 1),
            private_key=example_private_key("wg", 1),
            port=p1,
            peer_public_key=example_public_key("wg", 2),
            peer_allowed_ips=[],
        )
    )

    db._data.port_counter = 50004

    p2 = db.allocate_port(is_provider=True)
    assert p2 == 50003

    db._data.links.append(
        WireguardLink(
            owner=1,
            status=WireguardLinkStatus.OPEN,
            public_key=example_public_key("wg", 3),
            private_key=example_private_key("wg", 3),
            port=p2,
            peer_public_key=example_public_key("wg", 4),
            peer_allowed_ips=[],
        )
    )

    with pytest.raises(ValueError):
        db.allocate_port(is_provider=True)


def test_search_key_not_found(db):
    assert db.search_key(example_public_key("wg", 1)) is None


def test_link_action_not_found(db):
    with pytest.raises(KeyError, match="link not found"):
        db.acknowledge_open_link(example_public_key("wg", 1), example_public_key("wg", 2), "ep")


def test_update_link_endpoint_change(db):
    owner = 1
    public_key = example_public_key("wg", 1)
    private_key = example_private_key("wg", 1)
    peer = example_public_key("wg", 2)
    db.add_key(owner=owner, public_key=public_key, private_key=private_key)

    db.open_link(
        owner=owner,
        public_key=public_key,
        port=50000,
        peer_public_key=peer,
        allowed_ips=[],
        peer_endpoint="1.1.1.1:1111",
    )

    new_ep = "2.2.2.2:2222"
    db.update_link(public_key, peer, peer_endpoint=new_ep)

    link = db.search_link(public_key, peer)
    assert link.peer_endpoint == new_ep


def test_list_keys_filtered(db):
    db.add_key(
        owner=1,
        public_key=example_public_key("wg", 1),
        private_key=example_private_key("wg", 1),
    )
    db.add_key(
        owner=2,
        public_key=example_public_key("wg", 2),
        private_key=example_private_key("wg", 2),
    )

    keys1 = db.list_keys(owner=1)
    assert len(keys1) == 1
    assert keys1[0].owner == 1

    keys2 = db.list_keys(owner=2)
    assert len(keys2) == 1
    assert keys2[0].owner == 2
