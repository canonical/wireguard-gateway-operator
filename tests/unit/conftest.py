# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for charm unit tests."""

import pytest
from charmlibs import systemd

import bird
import charm
import wgdb
import wireguard
from tests.unit.helpers import example_public_key


@pytest.fixture(autouse=True)
def wgdb_path(tmp_path_factory, monkeypatch):
    monkeypatch.setattr(charm, "WGDB_DIR", tmp_path_factory.mktemp("wgdb"))


@pytest.fixture(autouse=True)
def get_bird_config(monkeypatch):
    bird_config = ""

    def mock_bird_reload(config: str):
        nonlocal bird_config
        bird_config = config

    def mock_get_router_id():
        return "172.16.0.0"

    monkeypatch.setattr(bird, "bird_install", lambda: None)
    monkeypatch.setattr(bird, "get_router_id", mock_get_router_id)
    monkeypatch.setattr(bird, "bird_reload", mock_bird_reload)

    return lambda: bird_config


@pytest.fixture(autouse=True)
def get_wireguard_config(monkeypatch):
    monkeypatch.setattr(systemd, "service_enable", lambda _: None)
    monkeypatch.setattr(systemd, "service_start", lambda _: None)
    monkeypatch.setattr(systemd, "service_disable", lambda _: None)
    monkeypatch.setattr(systemd, "service_stop", lambda _: None)
    monkeypatch.setattr(wireguard, "wireguard_install", lambda: None)

    config: dict[int, wgdb.WireguardLink] = {}

    def mock_wireguard_list():
        return list(config.values())

    def mock_wireguard_add(interface: wgdb.WireguardLink, is_provider: bool) -> None:
        config[interface.port] = interface

    def mock_wireguard_remove(interface: wgdb.WireguardLink) -> None:
        del config[interface.port]

    def mock_wireguard_syncconf(interface: wgdb.WireguardLink, is_provider: bool) -> None:
        config[interface.port] = interface

    monkeypatch.setattr(wireguard, "wireguard_list", mock_wireguard_list)
    monkeypatch.setattr(wireguard, "wireguard_add", mock_wireguard_add)
    monkeypatch.setattr(wireguard, "wireguard_remove", mock_wireguard_remove)
    monkeypatch.setattr(wireguard, "wireguard_syncconf", mock_wireguard_syncconf)

    return lambda: config


@pytest.fixture(autouse=True)
def generate_wireguard_keypair(monkeypatch):
    counter = 0

    def dummy_generate_keypair() -> wireguard.WireguardKeypair:
        nonlocal counter
        keypair = wireguard.WireguardKeypair(
            private_key=example_public_key("local", counter),
            public_key=example_public_key("local", counter),
        )
        counter += 1
        return keypair

    monkeypatch.setattr(charm.wireguard, "generate_keypair", dummy_generate_keypair)
