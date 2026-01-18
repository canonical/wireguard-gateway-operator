# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm unit test."""
import pytest
from ops import testing

import charm

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
    assert set(local_unit_data["public-keys"].split(",")) == {
        example_public_key("local", 0),
        example_public_key("local", 1),
    }


@pytest.mark.parametrize(
    "relation_name", ["provide-wireguard-router", "require-wireguard-router"]
)
def test_charm_populate_listen_ports_in_relation(relation_name: str):
    ctx = testing.Context(charm.Charm)
    relation = testing.Relation(
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
    if relation_name == "provide-wireguard-router":
        assert set(local_unit_data["listen-ports"].split(",")) == {
            f'{example_public_key("local",0)}:{example_public_key("remote1", 0)}:50000',
            f'{example_public_key("local",1)}:{example_public_key("remote1", 1)}:50001',
            f'{example_public_key("local", 0)}:{example_public_key("remote2", 0)}:50002',
            f'{example_public_key("local", 1)}:{example_public_key("remote2", 1)}:50003',
        }
    if relation_name == "require-wireguard-router":
        assert not local_unit_data.get("listen-ports")


def test_requirer_response_listen_ports_in_relation():
    ctx = testing.Context(charm.Charm)
    relation = testing.Relation(endpoint="require-wireguard-router", id=1)
    state_in = testing.State(relations=[relation], config={"tunnels": 2})
    state_out = ctx.run(ctx.on.config_changed(), state_in)
    local_unit_data = state_out.get_relation(relation.id).local_unit_data
    ctx = testing.Context(charm.Charm)
    relation = testing.Relation(
        id=1,
        endpoint="require-wireguard-router",
        local_unit_data=local_unit_data,
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
