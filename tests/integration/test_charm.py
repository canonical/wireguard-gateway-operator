#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests."""

import ipaddress
import json
import logging
import time

import jubilant
import pytest

logger = logging.getLogger(__name__)


@pytest.mark.abort_on_fail
def test_charm(juju: jubilant.Juju, wireguard_gateway_charm_file: str):
    """
    arrange: deploy two ubuntu units and two wireguard-gateway applications.
    act: integrate the two wireguard-gateway applications.
    assert: wait for all units to be active.
    """
    juju.deploy("ubuntu", "test-a")
    juju.deploy("ubuntu", "test-b")
    juju.deploy(
        wireguard_gateway_charm_file,
        "wireguard-a",
        config={"advertise-prefixes": "3fff::/20, 192.0.2.0/24"},
        num_units=2,
    )
    juju.deploy(
        wireguard_gateway_charm_file,
        "wireguard-b",
        config={"advertise-prefixes": "2001:db8::/32, 198.51.100.0/24"},
        num_units=2,
    )
    juju.integrate("wireguard-a:wireguard-router-a", "wireguard-b:wireguard-router-b")
    juju.wait(jubilant.all_active)


def wait_for_bird_route(juju: jubilant.Juju, unit: str, dst: str, nexthops: int) -> dict:
    deadline = time.time() + 30
    ipv6 = ipaddress.ip_network(dst).version == 6
    while time.time() < deadline:
        all_route = json.loads(
            juju.exec(f"ip {'-6' if ipv6 else '-4'} --json route", unit=unit).stdout
        )
        logger.info(f"route on {unit}: {all_route}")
        for route in all_route:
            if (
                route["dst"] == dst
                and len(route.get("nexthops", [])) >= nexthops
                and route["protocol"] == "bird"
            ):
                return route
        time.sleep(3)
    raise TimeoutError("timeout waiting for bird route")


def test_route_table(juju: jubilant.Juju):
    """
    arrange: get the status of the deployment.
    act: wait for bird routes to be propagated.
    assert: verify that bird routes are established with correct nexthops on both sides.
    """
    status = juju.status()

    for unit in status.get_units("wireguard-a"):
        wait_for_bird_route(juju, unit, dst="2001:db8::/32", nexthops=4)
        wait_for_bird_route(juju, unit, dst="198.51.100.0/24", nexthops=4)

    for unit in status.get_units("wireguard-b"):
        wait_for_bird_route(juju, unit, dst="3fff::/20", nexthops=4)
        wait_for_bird_route(juju, unit, dst="192.0.2.0/24", nexthops=4)


def test_routing(juju: jubilant.Juju):
    """
    arrange: configure vips and ip addresses on test and wireguard units.
    act: add routes and execute ping commands between test units.
    assert: verify success of ping commands to confirm routing.
    """
    juju.config("wireguard-a", {"vips": "203.0.113.2/24"})
    juju.wait(jubilant.all_active)

    status = juju.status()
    test_a_unit = next(iter(status.get_units("test-a")))
    test_a_address = status.get_units("test-a")[test_a_unit].public_address
    test_b_unit = next(iter(status.get_units("test-b")))
    test_b_address = status.get_units("test-b")[test_b_unit].public_address
    wireguard_b_unit = next(iter(status.get_units("wireguard-b")))
    wireguard_b_address = status.get_units("wireguard-b")[wireguard_b_unit].public_address

    juju.exec("sudo ip addr add 192.0.2.2/24 dev eth0", unit=test_a_unit)
    juju.exec("sudo ip addr add 203.0.113.3/24 dev eth0", unit=test_a_unit)
    juju.exec("sudo ip route add 198.51.100.0/24 via 203.0.113.2", unit=test_a_unit)
    for unit in status.get_units("wireguard-a"):
        juju.exec(f"sudo ip route add 192.0.2.2/32 via {test_a_address}", unit=unit)

    juju.exec("sudo ip addr add 198.51.100.2/24 dev eth0", unit=test_b_unit)
    juju.exec(f"sudo ip route add 192.0.2.0/24 via {wireguard_b_address}", unit=test_b_unit)
    for unit in status.get_units("wireguard-b"):
        juju.exec(f"sudo ip route add 198.51.100.2/32 via {test_b_address}", unit=unit)

    juju.exec("ping 198.51.100.2 -I 192.0.2.2 -c 1", unit=test_a_unit)
    juju.exec("ping 192.0.2.2 -I 198.51.100.2 -c 1", unit=test_b_unit)


def test_mtu(juju: jubilant.Juju):
    """
    arrange: set different MTUs on eth0 of one unit from each application.
    act: trigger reconfiguration and wait for active status.
    assert: verify wireguard interfaces on all units have the same MTU.
    """
    status = juju.status()
    wireguard_a_units = sorted(status.get_units("wireguard-a"))
    wireguard_b_units = sorted(status.get_units("wireguard-b"))

    juju.exec("sudo ip link set eth0 mtu 1400", unit=wireguard_a_units[0])
    juju.exec("sudo ip link set eth0 mtu 1360", unit=wireguard_b_units[0])

    juju.config("wireguard-a", {"vips": "203.0.113.2/24 "})
    juju.wait(jubilant.all_active)
    juju.config("wireguard-a", {"vips": "203.0.113.2/24"})
    juju.wait(jubilant.all_active)

    all_mtus = set()
    for unit in wireguard_a_units + wireguard_b_units:
        wg_interfaces_output = juju.exec("wg show interfaces", unit=unit).stdout.strip()
        assert wg_interfaces_output
        wg_interfaces = wg_interfaces_output.split()
        for iface in wg_interfaces:
            link_info = json.loads(juju.exec(f"ip -j link show {iface}", unit=unit).stdout)
            iface_mtu = link_info[0]["mtu"]
            logger.info(f"unit {unit} WireGuard interface {iface} mtu={iface_mtu}")
            all_mtus.add(iface_mtu)

    assert all_mtus == {1280}


def test_keepalived_interface(juju: jubilant.Juju):
    """
    arrange: set the wireguard-a VIPs configuration.
    act: read the keepalived configuration and determine the expected network interface.
    assert: verify that keepalived used network interface.
    """
    juju.config("wireguard-a", {"vips": "203.0.113.2/24"})
    juju.wait(jubilant.all_active)

    status = juju.status()

    for unit in status.get_units("wireguard-a"):
        keepalived_config = juju.exec("cat /etc/keepalived/keepalived.conf", unit=unit).stdout

        assert "eth0" in keepalived_config


def test_bird_metrics(juju: jubilant.Juju):
    juju.deploy("opentelemetry-collector", channel="2/stable", base="ubuntu@24.04")
    juju.integrate("wireguard-a:cos-agent", "opentelemetry-collector")
    juju.integrate("wireguard-b:cos-agent", "opentelemetry-collector")
    juju.wait(
        lambda s: jubilant.all_active(s, "wireguard-a", "wireguard-b")
        and jubilant.all_blocked(s, "opentelemetry-collector")
    )

    status = juju.status()
    for unit in status.get_units("wireguard-a"):
        juju.exec("curl -m 10 localhost:9324/metrics", unit=unit)
    for unit in status.get_units("wireguard-b"):
        juju.exec("curl -m 10 localhost:9324/metrics", unit=unit)
