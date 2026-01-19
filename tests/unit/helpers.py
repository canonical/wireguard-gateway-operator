# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit test helpers."""

import charm
import relations
import wgdb

__all__ = ["AssertRelationData", "example_private_key", "example_public_key", "load_wgdb"]


def example_public_key(name: str, n: int) -> str:
    """Generate a fake public key for testing.

    Args:
        name: Name to include in the key.
        n: Number to include in the key.

    Returns:
        Fake public key string.
    """
    padding = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    key = f"public/key/{name}/{n}/"
    return key + padding[len(key) :]


def example_private_key(name: str, n: int) -> str:
    """Generate a fake private key for testing.

    Args:
        name: Name to include in the key.
        n: Number to include in the key.

    Returns:
        Fake private key string.
    """
    padding = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    key = f"private/key/{name}/{n}/"
    return key + padding[len(key) :]


def load_wgdb() -> wgdb.WireguardDb:
    """Get the WireguardDb instance used in tests.

    Returns:
        The WireguardDb instance.
    """
    return wgdb.WireguardDb(file=charm.WGDB_DIR / "wireguard-gateway-0.json")


class AssertRelationData:
    """Helper to assert relation data in tests."""

    def __init__(self, relation_data: dict[str, str]):
        self.data = relations.WireguardRouterRelationData.model_validate(relation_data)
        ports = [port.port for port in self.data.listen_ports]
        assert len(ports) == len(set(ports)), "duplicate listen ports in relation data"

    def have_public_keys(self, *excepted_keys: str) -> None:
        """Check if the relation data has the expected public keys.

        Args:
            excepted_keys: Expected public keys.
        """
        for key in excepted_keys:
            assert key in self.data.public_keys

    def have_listen_port(
        self, public_key: str, peer_public_key: str, port: int | None = None
    ) -> None:
        """Check if the relation data has the expected listen port.

        Args:
            public_key: The public key.
            peer_public_key: The peer's public key.
            port: The expected port.
        """
        for listen_port in self.data.listen_ports:
            if (
                listen_port.public_key == public_key
                and listen_port.peer_public_key == peer_public_key
                and (port is None or listen_port.port == port)
            ):
                return
        assert False, f"{public_key}:{peer_public_key}:{port if port else '*'} not found"
