# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""WireGuard Database (wgdb) provides persistent storage for WireGuard peer and interface
information.

wgdb stores two main kinds of records:
 - keys: WireGuard public/private key pairs.
 - links: status of WireGuard interface.

We use the term link because, although a WireGuard interface can normally have multiple peers, our
ECMP use case requires each interface contains exactly one peer. That effectively turns the
interface into a point-to-point link between two peers.

A link moves through four states:
 - half_open:  The local side has sent a request to create a new WireGuard link and is waiting for
               the remote side to acknowledge it.
 - open:       The remote side has acknowledged the request and provided its peer endpoint
               information. In this state, the WireGuard interface is created on the system.
 - half_close: The local side has requested to remove the link and is waiting for the remote side
               to confirm. The WireGuard interface still exists to avoid dropping traffic if the
               remote side is still sending, but the local side should not send traffic through it.
 - close:      Both sides have acknowledged the closure. The WireGuard interface can be safely
               removed from the system.
"""

import datetime
import enum
import os
import pathlib
import secrets
import typing

import pydantic

_WIREGUARD_PORT_RANGE = (50000, 52000)


class WireguardLinkStatus(enum.StrEnum):
    """Enumeration for WireGuard link status."""

    HALF_OPEN = "half_open"
    OPEN = "open"
    HALF_CLOSE = "half_close"
    CLOSE = "close"


class WireguardKey(pydantic.BaseModel):
    """WireGuard public/private key pair."""

    private_key: str
    public_key: str


class WireguardLink(pydantic.BaseModel):
    """WireGuard link information."""

    status: WireguardLinkStatus
    opened_at: datetime.datetime | None = None
    closed_at: datetime.datetime | None = None
    public_key: str
    port: int
    peer_public_key: str
    peer_endpoint: str | None = None


class _WireguardDbSchema(pydantic.BaseModel):
    """Internal database schema."""

    port_counter: int = pydantic.Field(default=_WIREGUARD_PORT_RANGE[0])
    keys: typing.List[WireguardKey] = pydantic.Field(default_factory=list)
    links: typing.List[WireguardLink] = pydantic.Field(default_factory=list)


class WireguardDb:
    """Persistent storage for WireGuard peer and interface information."""

    def __init__(self, file: str):
        """Initialize the database.

        Args:
            file: Path to the JSON database file.
        """
        self.file = pathlib.Path(file)
        self._data = self._load()
        if not self.file.exists():
            self._save()

    def _utc_now(self) -> datetime.datetime:
        """Get current UTC datetime.

        Returns:
            Current datetime in UTC.
        """
        return datetime.datetime.now(datetime.timezone.utc)

    def _load(self) -> _WireguardDbSchema:
        """Load database from file.

        Returns:
            Loaded database schema.
        """
        if self.file.exists():
            return _WireguardDbSchema.model_validate_json(
                self.file.read_text(encoding="utf-8")
            )
        else:
            return _WireguardDbSchema()

    def _save(self):
        """Save database to file."""
        tmp_file = self.file.with_suffix(f".{secrets.token_urlsafe(8)}")
        tmp_file.touch(mode=0o600)
        tmp_file.write_text(self._data.model_dump_json(indent=2), encoding="utf-8")
        os.rename(tmp_file, self.file)

    def allocate_port(self) -> int:
        """Allocates an unused port from the configured range.

        Returns:
            An integer representing the allocated port.

        Raises:
            ValueError: If no ports are available in the range.
        """
        used = set(l.port for l in self._data.links)
        for port in range(self._data.port_counter, _WIREGUARD_PORT_RANGE[1]):
            if port in used:
                continue
            self._data.port_counter = port
            return port
        for port in range(*_WIREGUARD_PORT_RANGE):
            if port in used:
                continue
            self._data.port_counter = port
            return port
        raise ValueError(
            "all ports in the configured WireGuard port range are already in use"
        )

    def _search_key(self, public_key: str) -> WireguardKey | None:
        """Search for a key pair in database.

        The returned key pair is a reference to the key pair inside the database, modifying it
        will change the database content.

        Args:
            public_key: The public key to search.

        Returns:
            The key object if found, None otherwise.
        """
        for key in self._data.keys:
            if key.public_key == public_key:
                return key
        return None

    def search_key(self, public_key: str) -> WireguardKey | None:
        """Searches for a key pair by public key.

        Args:
            public_key: The public key to search for.

        Returns:
            A WireguardKey object if found, None otherwise.
        """
        key = self._search_key(public_key)
        if key:
            return key.model_copy(deep=True)
        return None

    def add_key(self, *, public_key: str, private_key: str) -> None:
        """Adds a new key pair to the database.

        Args:
            public_key: The public key.
            private_key: The private key.
        """
        self._data.keys.append(
            WireguardKey(public_key=public_key, private_key=private_key)
        )
        self._save()

    def remove_key(self, public_key: str) -> None:
        """Removes a key pair from the database.

        Args:
            public_key: The public key of the pair to remove.
        """
        self._data.keys = [k for k in self._data.keys if k.public_key == public_key]
        self._save()

    def _search_link(
        self, public_key: str, peer_public_key: str
    ) -> WireguardLink | None:
        """Search for a link in database.

        The returned link object is a reference to the object inside the database. modifying it
        will change the database content.

        Args:
            public_key: The local public key.
            peer_public_key: The peer public key.

        Returns:
            The link object if found, None otherwise.
        """
        for link in self._data.links:
            if (
                link.public_key == public_key
                and link.peer_public_key == peer_public_key
            ):
                return link
        return None

    def _must_search_link(self, public_key: str, peer_public_key: str) -> WireguardLink:
        """Search for a link, raising error if not found.

        The returned link object is a reference to the object inside the database. modifying it
        will change the database content.

        Args:
            public_key: The local public key.
            peer_public_key: The peer public key.

        Returns:
            The link object.

        Raises:
            KeyError: If link not found.
        """
        link = self._search_link(public_key, peer_public_key)
        if not link:
            raise KeyError("link not found in the database")
        return link

    def search_link(
        self, public_key: str, peer_public_key: str
    ) -> WireguardLink | None:
        """Searches for a link by local and peer public keys.

        Args:
            public_key: The local public key.
            peer_public_key: The peer's public key.

        Returns:
            A WireguardLink object if found, None otherwise.
        """
        link = self._search_link(public_key, peer_public_key)
        if link:
            return link.model_copy(deep=True)
        return None

    def add_link(self, *, public_key: str, port: int, peer_public_key: str):
        """Creates a new half open link in the database.

        Args:
            public_key: The local public key.
            port: The local listen port.
            peer_public_key: The peer's public key.
        """
        self._data["links"].append(
            WireguardLink(
                status=WireguardLinkStatus.HALF_OPEN,
                public_key=public_key,
                port=port,
                peer_public_key=peer_public_key,
            )
        )
        self._save()

    def acknowledge_open_link(
        self, public_key: str, peer_public_key: str, peer_endpoint: str
    ) -> None:
        """Transitions a link to open state upon peer acknowledgement.

        Args:
            public_key: The local public key.
            peer_public_key: The peer's public key.
            peer_endpoint: The endpoint address of the peer.

        Raises:
            KeyError: If the link is not found.
        """
        link = self._must_search_link(public_key, peer_public_key)
        link.status = WireguardLinkStatus.OPEN
        link.opened_at = self._utc_now()
        link.peer_endpoint = peer_endpoint
        self._save()

    def close_link(self, public_key: str, peer_public_key: str) -> None:
        """Transitions a link to half close state.

        Args:
            public_key: The local public key.
            peer_public_key: The peer's public key.

        Raises:
            KeyError: If the link is not found.
        """
        link = self._must_search_link(public_key, peer_public_key)
        link.status = WireguardLinkStatus.HALF_CLOSE
        link.closed_at = self._utc_now()
        self._save()

    def acknowledge_close_link(self, public_key: str, peer_public_key: str) -> None:
        """Transitions a link to close state.

        Args:
            public_key: The local public key.
            peer_public_key: The peer's public key.

        Raises:
            KeyError: If the link is not found.
        """
        link = self._must_search_link(public_key, peer_public_key)
        link.status = WireguardLinkStatus.CLOSE
        self._save()

    def remove_link(self, public_key: str, peer_public_key: str) -> None:
        """Removes a link record from the database.

        Args:
            public_key: The local public key.
            peer_public_key: The peer's public key.
        """
        self._data.links = [
            l
            for l in self._data.links
            if l.public_key == public_key and l.peer_public_key == peer_public_key
        ]
        self._save()
