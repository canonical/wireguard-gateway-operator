# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm unit test."""

import textwrap

import pytest
from ops import testing

import charm
import wgdb
from tests.unit.helpers import (
    AssertRelationData,
    example_private_key,
    example_public_key,
    load_wgdb,
)

BASIC_CONFIG = {"tunnels": 2, "advertise-prefixes": "2001:DB8::/32, 192.0.2.0/24"}


@pytest.mark.parametrize(
    "relation_name",
    [
        charm.WIREGUARD_ROUTER_PROVIDER_RELATION,
        charm.WIREGUARD_ROUTER_REQUIRER_RELATION,
    ],
)
def test_charm_populate_public_key_in_relation(relation_name: str):
    """
    arrange: create context, relation, and state with basic config.
    act: run config_changed event.
    assert: verify public keys are populated in local unit data and db.
    """
    ctx = testing.Context(charm.Charm)
    relation = testing.Relation(endpoint=relation_name)
    state_in = testing.State(relations=[relation], config=BASIC_CONFIG)
    state_out = ctx.run(ctx.on.config_changed(), state_in)
    local_unit_data = state_out.get_relation(relation.id).local_unit_data
    expected_public_keys = {
        example_public_key("local", 0),
        example_public_key("local", 1),
    }
    assert_relation = AssertRelationData(local_unit_data)
    assert set(assert_relation.data.public_keys) == expected_public_keys
    db = load_wgdb()
    assert {k.public_key for k in db.list_keys(owner=relation.id)} == expected_public_keys


@pytest.mark.parametrize(
    "relation_name",
    [
        charm.WIREGUARD_ROUTER_PROVIDER_RELATION,
        charm.WIREGUARD_ROUTER_REQUIRER_RELATION,
    ],
)
def test_charm_populate_listen_ports_in_relation(relation_name: str):
    """
    arrange: create context with remote unit data.
    act: run config_changed event.
    assert: verify listen ports are populated in local unit data, and links are created in db.
    """
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
    state_in = testing.State(relations=[relation], config=BASIC_CONFIG)
    state_out = ctx.run(ctx.on.config_changed(), state_in)
    local_unit_data = state_out.get_relation(relation.id).local_unit_data
    assert_relation = AssertRelationData(local_unit_data)
    db = load_wgdb()
    if relation_name == charm.WIREGUARD_ROUTER_PROVIDER_RELATION:
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
    if relation_name == charm.WIREGUARD_ROUTER_REQUIRER_RELATION:
        assert not assert_relation.data.listen_ports


def test_requirer_response_listen_ports_in_relation():
    """
    arrange: setup db with local keys and relation with remote public keys/listen ports.
    act: run config_changed event.
    assert: verify local unit data parses listen ports and links are open in db.
    """
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
        endpoint=charm.WIREGUARD_ROUTER_REQUIRER_RELATION,
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
    state_in = testing.State(relations=[relation], config=BASIC_CONFIG)
    state_out = ctx.run(ctx.on.config_changed(), state_in)
    local_unit_data = state_out.get_relation(relation.id).local_unit_data
    assert len(local_unit_data["listen-ports"].split(",")) == 4
    db = load_wgdb()
    assert len(db.list_link(owner=1)) == 4
    for link in db.list_link(owner=1):
        assert link.status == wgdb.WireguardLinkStatus.OPEN


@pytest.mark.parametrize("remote_public_keys", [1, 2, 3])
def test_nonequal_public_key_numbers(remote_public_keys):
    """
    arrange: create context with variable number of remote public keys.
    act: run config_changed event.
    assert: verify correct number of listen ports and links created.
    """
    ctx = testing.Context(charm.Charm)
    relation = testing.Relation(
        id=1,
        endpoint=charm.WIREGUARD_ROUTER_PROVIDER_RELATION,
        remote_units_data={
            1: {
                "ingress-address": "172.16.0.1",
                "public-keys": ",".join(
                    [example_public_key("remote1", i) for i in range(remote_public_keys)]
                ),
            }
        },
    )
    state_in = testing.State(relations=[relation], config=BASIC_CONFIG)
    state_out = ctx.run(ctx.on.config_changed(), state_in)
    local_unit_data = state_out.get_relation(relation.id).local_unit_data
    assert_relation = AssertRelationData(local_unit_data)
    assert len(assert_relation.data.listen_ports) == min(2, remote_public_keys)
    db = load_wgdb()
    assert len(db.list_keys(owner=1)) == 2
    assert len(db.list_link(owner=1)) == min(2, remote_public_keys)


@pytest.mark.parametrize(
    "relation_name",
    [
        charm.WIREGUARD_ROUTER_PROVIDER_RELATION,
        charm.WIREGUARD_ROUTER_REQUIRER_RELATION,
    ],
)
def test_remote_remove_listen_ports(relation_name: str):
    """
    arrange: setup db with pre-existing links and context where remote data changes.
    act: run config_changed event.
    assert: verify links are closed/updated correctly in db when listen-ports is removed in remote.
    """
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
    state_in = testing.State(relations=[relation], config=BASIC_CONFIG)
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
    "relation_name",
    [
        charm.WIREGUARD_ROUTER_PROVIDER_RELATION,
        charm.WIREGUARD_ROUTER_REQUIRER_RELATION,
    ],
)
@pytest.mark.parametrize(
    "link_state",
    [
        wgdb.WireguardLinkStatus.HALF_OPEN,
        wgdb.WireguardLinkStatus.OPEN,
        wgdb.WireguardLinkStatus.HALF_CLOSE,
    ],
)
def test_remote_remove_public_keys(relation_name: str, link_state: wgdb.WireguardLinkStatus):
    """
    arrange: setup db with pre-existing links and context where remote data changes.
    act: run config_changed event.
    assert: verify links are closed in db when public key is removed in the remote.
    """
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
    state_in = testing.State(relations=[relation], config=BASIC_CONFIG)
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


def test_charm_remove_relation():
    """
    arrange: setup db with keys and links.
    act: run config_changed event with empty relations.
    assert: verify keys are retired and links are closed when relation is removed.
    """
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
    )
    ctx = testing.Context(charm.Charm)
    state_in = testing.State(relations=[], config=BASIC_CONFIG)
    ctx.run(ctx.on.config_changed(), state_in)
    db = load_wgdb()
    assert db.search_key(public_key=example_public_key("local", 0)).retired
    assert (
        db.search_link(
            public_key=example_public_key("local", 0),
            peer_public_key=example_public_key("remote1", 0),
        ).status
        == wgdb.WireguardLinkStatus.CLOSE
    )


def test_charm_configure_bird_wireguard_keepalived(
    get_bird_config, get_wireguard_config, get_keepalived_config
):
    """
    arrange: setup db and context/relation with remote data including advertise-prefixes.
    act: run config_changed event.
    assert: verify bird, wireguard, and keepalived configurations are generated correctly.
    """
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
        peer_endpoint="172.16.0.1:50000",
    )
    ctx = testing.Context(charm.Charm)
    relation = testing.Relation(
        id=1,
        endpoint=charm.WIREGUARD_ROUTER_PROVIDER_RELATION,
        remote_units_data={
            1: {
                "ingress-address": "172.16.0.1",
                "public-keys": example_public_key("remote1", 0),
                "advertise-prefixes": "10.0.0.0/24",
                "listen-ports": ":".join(
                    [
                        example_public_key("remote1", 0),
                        example_public_key("local", 0),
                        "50000",
                    ]
                ),
            }
        },
    )
    config = dict(BASIC_CONFIG)
    config["vips"] = "172.16.0.200/24"
    state_in = testing.State(relations=[relation], config=config)
    ctx.run(ctx.on.config_changed(), state_in)
    assert (
        get_bird_config().strip()
        == textwrap.dedent(
            """\
            router id 172.16.0.0;

            protocol kernel k4 {
              ipv4 { import none; export all; };
              merge paths yes limit 64;
            }

            protocol kernel k6 {
              ipv6 { import none; export all; };
              merge paths yes limit 64;
            }

            protocol device {}

            protocol ospf v3 OSPF6 {
              rfc5838 yes;
              ecmp yes limit 64;
              instance id 0;
              ipv6 { import all; export none; };

              area 0.0.0.0 {
                interface "wg50000" { type ptp; cost 10; hello 5; dead 30; };
                stubnet 2001:db8::/32 { cost 10; };
              };
            }

            protocol ospf v3 OSPF4 {
              rfc5838 yes;
              ecmp yes limit 64;
              instance id 64;
              ipv4 { import all; export none; };

              area 0.0.0.0 {
                interface "wg50000" { type ptp; cost 10; hello 5; dead 30; };
                stubnet 169.254.0.0/24 { hidden; };
                stubnet 192.0.2.0/24 { cost 10; };
              };
            }
            """
        ).strip()
    )
    assert len(get_wireguard_config()) == 1
    wireguard_config = next(iter(get_wireguard_config().values()))
    assert wireguard_config.peer_endpoint == "172.16.0.1:50000"
    assert wireguard_config.public_key == example_public_key("local", 0)
    assert wireguard_config.peer_public_key == example_public_key("remote1", 0)
    assert (
        get_keepalived_config().strip()
        == textwrap.dedent(
            """\
            global_defs {
              router_id 172.16.0.0
            }

            vrrp_script check_route_0 {
              script "/check_route 10.0.0.0/24"
              interval 2
              timeout 1
              fall 1
              rise 1
            }

            vrrp_instance vrrp_0 {
              state BACKUP
              interface eth0
              virtual_router_id 1
              priority 127
              advert_int 1

              virtual_ipaddress {
                172.16.0.200/24 dev eth0
              }
            }

            vrrp_sync_group vrrp_group {
              group {
                vrrp_0
              }

              track_script {
                check_route_0 weight -1
              }
            }
            """
        ).strip()
    )
