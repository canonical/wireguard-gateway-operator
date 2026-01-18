# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for charm unit tests."""

import pytest

import wireguard

from tests.unit.helpers import *


@pytest.fixture(autouse=True)
def wgdb_path(tmp_path_factory, monkeypatch):
    monkeypatch.setattr(charm, "_WGDB_DIR", tmp_path_factory.mktemp("wgdb"))


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
