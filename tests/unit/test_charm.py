# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm unit test."""

import pytest
from ops import testing

import wgdb
from tests.unit.helpers import *


@pytest.mark.parametrize(
    "relation_name", ["provide-wireguard-router", "require-wireguard-router"]
)
def test_charm_populate_public_key_in_relation(relation_name: str):
    ctx = testing.Context(charm.Charm)
    relation = testing.Relation(endpoint=relation_name)
    state_in = testing.State(relations=[relation], config={"tunnels": 2})
    state_out = ctx.run(ctx.on.config_changed(), state_in)
    local_unit_data = state_out.get_relation(relation.id).local_unit_data
    expected_public_keys = {
        example_public_key("local", 0),
        example_public_key("local", 1),
    }
    assert_relation = AssertRelationData(local_unit_data)
    assert set(assert_relation.data.public_keys) == expected_public_keys
    db = load_wgdb()
    assert (
        set(k.public_key for k in db.list_keys(owner=relation.id))
        == expected_public_keys
    )


@pytest.mark.parametrize(
    "relation_name", ["provide-wireguard-router", "require-wireguard-router"]
)
def test_charm_populate_listen_ports_in_relation(relation_name: str):
    ctx = testing.Context(charm.Charm)
    relation = testing.Relation(
        id=1,
        endpoint=relation_name,
        remote_units_data={
            1: {
                "public-keys": ",".join(
                    [example_public_key("remote1", 0), example_public_key("remote1", 1)]
                ),
                "ingress-address": "172.16.0.1",
            },
            2: {
                "public-keys": ",".join(
                    [example_public_key("remote2", 0), example_public_key("remote2", 1)]
                ),
                "ingress-address": "172.16.0.2",
            },
        },
    )
    state_in = testing.State(relations=[relation], config={"tunnels": 2})
    state_out = ctx.run(ctx.on.config_changed(), state_in)
    local_unit_data = state_out.get_relation(relation.id).local_unit_data
    assert_relation = AssertRelationData(local_unit_data)
    db = load_wgdb()
    if relation_name == "provide-wireguard-router":
        assert_relation.have_listen_port(
            example_public_key("local", 0), example_public_key("remote1", 0)
        )
        assert_relation.have_listen_port(
            example_public_key("local", 1), example_public_key("remote1", 1)
        )
        assert_relation.have_listen_port(
            example_public_key("local", 0), example_public_key("remote2", 0)
        )
        assert_relation.have_listen_port(
            example_public_key("local", 1), example_public_key("remote2", 1)
        )
        assert len(assert_relation.data.listen_ports) == 4
        assert len(db.list_link(owner=1)) == 4
        for link in db.list_link(owner=1):
            assert link.status == wgdb.WireguardLinkStatus.HALF_OPEN
    if relation_name == "require-wireguard-router":
        assert not assert_relation.data.listen_ports


def test_requirer_response_listen_ports_in_relation():
    db = load_wgdb()
    db.add_key(
        owner=1,
        public_key=example_public_key("local", 0),
        private_key=example_public_key("local", 0),
    )
    db.add_key(
        owner=1,
        public_key=example_public_key("local", 1),
        private_key=example_public_key("local", 1),
    )
    ctx = testing.Context(charm.Charm)
    relation = testing.Relation(
        id=1,
        endpoint="require-wireguard-router",
        local_unit_data={
            "ingress-address": "172.16.0.0",
            "public-keys": ",".join(
                [example_public_key("local", 0), example_public_key("local", 1)]
            ),
        },
        remote_units_data={
            1: {
                "ingress-address": "172.16.0.1",
                "public-keys": ",".join(
                    [
                        example_public_key("remote1", 0),
                        example_public_key("remote1", 1),
                    ]
                ),
                "listen-ports": ",".join(
                    [
                        ":".join(
                            [
                                example_public_key("remote1", 0),
                                example_public_key("local", 0),
                                "50001",
                            ]
                        ),
                        ":".join(
                            [
                                example_public_key("remote1", 1),
                                example_public_key("local", 1),
                                "50002",
                            ]
                        ),
                    ]
                ),
            },
            2: {
                "ingress-address": "172.16.0.2",
                "public-keys": ",".join(
                    [
                        example_public_key("remote2", 0),
                        example_public_key("remote2", 1),
                    ]
                ),
                "listen-ports": ",".join(
                    [
                        ":".join(
                            [
                                example_public_key("remote2", 0),
                                example_public_key("local", 0),
                                "50003",
                            ]
                        ),
                        ":".join(
                            [
                                example_public_key("remote2", 1),
                                example_public_key("local", 1),
                                "50004",
                            ]
                        ),
                    ]
                ),
            },
        },
    )
    state_in = testing.State(relations=[relation], config={"tunnels": 2})
    state_out = ctx.run(ctx.on.config_changed(), state_in)
    local_unit_data = state_out.get_relation(relation.id).local_unit_data
    assert len(local_unit_data["listen-ports"].split(",")) == 4
    db = load_wgdb()
    assert len(db.list_link(owner=1)) == 4
    for link in db.list_link(owner=1):
        assert link.status == wgdb.WireguardLinkStatus.OPEN


@pytest.mark.parametrize("remote_public_keys", [1, 2, 3])
def test_nonequal_public_key_numbers(remote_public_keys):
    ctx = testing.Context(charm.Charm)
    relation = testing.Relation(
        id=1,
        endpoint="provide-wireguard-router",
        remote_units_data={
            1: {
                "ingress-address": "172.16.0.1",
                "public-keys": ",".join(
                    [
                        example_public_key("remote1", i)
                        for i in range(remote_public_keys)
                    ]
                ),
            }
        },
    )
    state_in = testing.State(relations=[relation], config={"tunnels": 2})
    state_out = ctx.run(ctx.on.config_changed(), state_in)
    local_unit_data = state_out.get_relation(relation.id).local_unit_data
    assert_relation = AssertRelationData(local_unit_data)
    assert len(assert_relation.data.listen_ports) == min(2, remote_public_keys)
    db = load_wgdb()
    assert len(db.list_keys(owner=1)) == 2
    assert len(db.list_link(owner=1)) == min(2, remote_public_keys)


@pytest.mark.parametrize(
    "relation_name", ["provide-wireguard-router", "require-wireguard-router"]
)
def test_remote_remove_listen_ports(relation_name: str):
    db = load_wgdb()
    for i in range(3):
        db.add_key(
            owner=1,
            public_key=example_public_key("local", i),
            private_key=example_private_key("local", i),
        )
    db.open_link(
        owner=1,
        public_key=example_public_key("local", 0),
        port=50000,
        peer_public_key=example_public_key("remote1", 0),
        allowed_ips=[],
        peer_endpoint="172.16.0.1:50000",
    )
    db.open_link(
        owner=1,
        public_key=example_public_key("local", 1),
        port=50001,
        peer_public_key=example_public_key("remote1", 1),
        allowed_ips=[],
    )
    db.open_link(
        owner=1,
        public_key=example_public_key("local", 2),
        peer_public_key=example_public_key("remote1", 2),
        port=50002,
        allowed_ips=[],
    )
    db.close_link(
        public_key=example_public_key("local", 2),
        peer_public_key=example_public_key("remote1", 2),
    )
    ctx = testing.Context(charm.Charm)
    relation = testing.Relation(
        id=1,
        endpoint=relation_name,
        remote_units_data={
            1: {
                "ingress-address": "172.16.0.1",
                "public-keys": ",".join(
                    [
                        example_public_key("remote1", 0),
                        example_public_key("remote1", 1),
                        example_public_key("remote1", 2),
                    ]
                ),
            }
        },
    )
    state_in = testing.State(relations=[relation], config={"tunnels": 2})
    state_out = ctx.run(ctx.on.config_changed(), state_in)
    local_unit_data = state_out.get_relation(relation.id).local_unit_data
    assert_relation = AssertRelationData(local_unit_data)
    assert len(assert_relation.data.listen_ports) == 1
    assert_relation.have_listen_port(
        public_key=example_public_key("local", 1),
        peer_public_key=example_public_key("remote1", 1),
        port=50001,
    )
    db = load_wgdb()
    assert (
        db.search_link(
            public_key=example_public_key("local", 0),
            peer_public_key=example_public_key("remote1", 0),
        ).status
        == wgdb.WireguardLinkStatus.CLOSE
    )
    assert (
        db.search_link(
            public_key=example_public_key("local", 1),
            peer_public_key=example_public_key("remote1", 1),
        ).status
        == wgdb.WireguardLinkStatus.HALF_OPEN
    )
    assert (
        db.search_link(
            public_key=example_public_key("local", 2),
            peer_public_key=example_public_key("remote1", 2),
        ).status
        == wgdb.WireguardLinkStatus.CLOSE
    )

@pytest.mark.parametrize(
    "relation_name", ["provide-wireguard-router", "require-wireguard-router"]
)
@pytest.mark.parametrize(
    "link_state",
    [
        wgdb.WireguardLinkStatus.HALF_OPEN,
        wgdb.WireguardLinkStatus.OPEN,
        wgdb.WireguardLinkStatus.HALF_CLOSE,
    ],
)
def test_remote_remove_public_keys(
    relation_name: str, link_state: wgdb.WireguardLinkStatus
):
    db = load_wgdb()
    db.add_key(
        owner=1,
        public_key=example_public_key("local", 0),
        private_key=example_private_key("local", 0),
    )
    db.open_link(
        owner=1,
        public_key=example_public_key("local", 0),
        port=50000,
        peer_public_key=example_public_key("remote1", 0),
        allowed_ips=[],
        peer_endpoint=(
            "172.16.0.1:50000" if link_state == wgdb.WireguardLinkStatus.OPEN else None
        ),
    )
    if link_state == wgdb.WireguardLinkStatus.HALF_CLOSE:
        db.close_link(
            public_key=example_public_key("local", 0),
            peer_public_key=example_public_key("remote1", 0),
        )
    ctx = testing.Context(charm.Charm)
    relation = testing.Relation(
        id=1,
        endpoint=relation_name,
        remote_units_data={
            1: {
                "ingress-address": "172.16.0.1",
            }
        },
    )
    state_in = testing.State(relations=[relation], config={"tunnels": 2})
    state_out = ctx.run(ctx.on.config_changed(), state_in)
    local_unit_data = state_out.get_relation(relation.id).local_unit_data
    assert_relation = AssertRelationData(local_unit_data)
    assert len(assert_relation.data.listen_ports) == 0
    db = load_wgdb()
    assert (
        db.search_link(
            public_key=example_public_key("local", 0),
            peer_public_key=example_public_key("remote1", 0),
        ).status
        == wgdb.WireguardLinkStatus.CLOSE
    )
