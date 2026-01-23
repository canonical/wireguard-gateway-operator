#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests."""

import json
import logging
import time
import typing

import jubilant
import pytest

logger = logging.getLogger(__name__)


@pytest.mark.abort_on_fail
def test_charm(juju: jubilant.Juju, wireguard_gateway_charm_file: str):
    juju.deploy(
        wireguard_gateway_charm_file,
        "wireguard-a",
        config={"advertise-prefixes": "192.0.2.0/24"},
        num_units=2,
    )
    juju.deploy(
        wireguard_gateway_charm_file,
        "wireguard-b",
        config={"advertise-prefixes": "2001:db8::/32"},
        num_units=2,
    )
    juju.integrate("wireguard-a:wireguard-router-a", "wireguard-b:wireguard-router-b")
    juju.wait(jubilant.all_active)


def wait_for_bird_route(juju: jubilant.Juju, unit: str, ipv6: bool, nexthops: int) -> list:
    deadline = time.time() + 30
    while time.time() < deadline:
        all_route = json.loads(
            juju.exec(f"ip {'-6' if ipv6 else '-4'} --json route", unit=unit).stdout
        )
        logger.info(f"route on {unit}: {all_route}")
        bird_route = [route for route in all_route if route["protocol"] == "bird"]
        if bird_route and len(bird_route[0]["nexthops"]) >= nexthops:
            return bird_route
        else:
            time.sleep(3)
    raise TimeoutError("timeout waiting for bird route")


def test_route(juju: jubilant.Juju):
    status = juju.status()

    for unit in status.get_units("wireguard-a"):
        bird_route = wait_for_bird_route(juju, unit, ipv6=True, nexthops=4)
        assert bird_route[0]["dst"] == "2001:db8::/32"
        assert len(bird_route[0]["nexthops"]) == 4

    for unit in status.get_units("wireguard-b"):
        bird_route = wait_for_bird_route(juju, unit, ipv6=False, nexthops=4)
        assert bird_route[0]["dst"] == "192.0.2.0/24"
        assert len(bird_route[0]["nexthops"]) == 4
