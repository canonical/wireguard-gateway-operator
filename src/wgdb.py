# Copyright 2026 Canonical Ltd.
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
import ipaddress
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

    owner: int
    private_key: str
    public_key: str
    retired: bool
    added_at: datetime.datetime
    retired_at: datetime.datetime | None = None


class WireguardLink(pydantic.BaseModel):
    """WireGuard link information."""

    owner: int
    status: WireguardLinkStatus
    opened_at: datetime.datetime | None = None
    closed_at: datetime.datetime | None = None
    public_key: str
    private_key: str
    port: int
    peer_public_key: str
    peer_endpoint: str | None = None
    peer_allowed_ips: list[ipaddress.IPv4Network | ipaddress.IPv6Network]

    @pydantic.field_validator("peer_allowed_ips", mode="before")
    @classmethod
    def _validate_peer_allowed_ips(
        cls, ips: list[str | ipaddress.IPv4Network | ipaddress.IPv6Network]
    ) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
        """Validate and convert peer_allowed_ips input.

        Args:
            ips: peer_allowed_ips input.

        Returns:
            Verified and converted peer_allowed_ips input.
        """
        result = []
        for ip in ips:
            if isinstance(ip, ipaddress.IPv4Network) or isinstance(
                ip, ipaddress.IPv6Network
            ):
                result.append(ip)
            else:
                result.append(ipaddress.ip_network(ip.strip(), strict=False))
        return result

    @property
    def interface_name(self) -> str:
        """Get the WireGuard interface name for this link.

        Returns:
            The WireGuard interface name.
        """
        return f"wg{self.port}"


class _WireguardDbSchema(pydantic.BaseModel):
    """Internal database schema."""

    port_counter: int = pydantic.Field(default=_WIREGUARD_PORT_RANGE[0])
    keys: typing.List[WireguardKey] = pydantic.Field(default_factory=list)
    links: typing.List[WireguardLink] = pydantic.Field(default_factory=list)


class WireguardDb:
    """Persistent storage for WireGuard peer and interface information."""

    def __init__(self, file: str | pathlib.Path):
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

    def list_keys(
        self, owner: int, include_retired: bool = False
    ) -> list[WireguardKey]:
        """Lists all key pairs for a given owner.

        Args:
            owner: The id of the relation owning the keys.
            include_retired: Whether to include retired keys.

        Returns:
            A list of WireguardKey objects.
        """
        return [
            key.model_copy(deep=True)
            for key in self._data.keys
            if key.owner == owner and (include_retired or not key.retired)
        ]

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

    def add_key(self, *, owner: int, public_key: str, private_key: str) -> None:
        """Adds a new key pair to the database.

        Args:
            owner: The id of the relation owning this key.
            public_key: The public key.
            private_key: The private key.
        """
        self._data.keys.append(
            WireguardKey(
                owner=owner,
                public_key=public_key,
                private_key=private_key,
                retired=False,
                added_at=self._utc_now(),
            )
        )
        self._save()

    def retire_key(self, public_key: str) -> None:
        """Marks a key pair as retired in the database.

        Args:
            public_key: The public key of the pair to retire.
        """
        key = self._search_key(public_key)
        if key is None:
            raise KeyError("public key not found in the database")
        key.retired = True
        key.retired_at = self._utc_now()
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

    def list_link(
        self,
        owner: int,
        include_closed: bool = False,
        include_half_closed: bool = False,
    ) -> list[WireguardLink]:
        """Lists all links for a given owner.

        Args:
            owner: The id of the relation owning the links.
            include_closed: Whether to include closed links.
            include_half_closed: Whether to include half-closed links.

        Returns:
            A list of WireguardLink objects.
        """
        return [
            link.model_copy(deep=True)
            for link in self._data.links
            if link.owner == owner
            and (include_closed or link.status != WireguardLinkStatus.CLOSE)
            and (include_half_closed or link.status != WireguardLinkStatus.HALF_CLOSE)
        ]

    def open_link(
        self,
        *,
        owner: int,
        public_key: str,
        port: int,
        peer_public_key: str,
        allowed_ips: list[ipaddress.IPv4Network | ipaddress.IPv6Network],
        peer_endpoint: str | None = None,
    ) -> None:
        """Creates a new half open link in the database.

        Args:
            owner: The id of the relation owning this link.
            public_key: The local public key.
            port: The local listen port.
            peer_public_key: The peer's public key.
            allowed_ips: The peer's allowed ips.
            peer_endpoint: The endpoint address of the peer.
        """
        key = self._search_key(public_key)
        if key is None:
            raise KeyError("public key not found in the database")
        self._data.links.append(
            WireguardLink(
                owner=owner,
                status=(
                    WireguardLinkStatus.HALF_OPEN
                    if not peer_endpoint
                    else WireguardLinkStatus.OPEN
                ),
                opened_at=self._utc_now(),
                public_key=public_key,
                private_key=key.private_key,
                port=port,
                peer_public_key=peer_public_key,
                peer_allowed_ips=allowed_ips,
                peer_endpoint=peer_endpoint,
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
        link.peer_endpoint = peer_endpoint
        self._save()

    def close_link(
        self, public_key: str, peer_public_key: str, acknowledged: bool = False
    ) -> None:
        """Transitions a link to half close state.

        Args:
            public_key: The local public key.
            peer_public_key: The peer's public key.
            acknowledged: Whether the close is already acknowledged by the peer.

        Raises:
            KeyError: If the link is not found.
        """
        link = self._must_search_link(public_key, peer_public_key)
        link.status = (
            WireguardLinkStatus.HALF_CLOSE
            if not acknowledged
            else WireguardLinkStatus.CLOSE
        )
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

    def update_link(
        self,
        public_key: str,
        peer_public_key: str,
        peer_endpoint: str | None = None,
        peer_allowed_ips: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = None,
    ) -> None:
        """Update link information in the database.

        Args:
            public_key: The local public key.
            peer_public_key: The peer's public key.
            peer_endpoint: The endpoint address of the peer.
            peer_allowed_ips: The peer's allowed ips.
        """
        link = self._must_search_link(
            public_key=public_key, peer_public_key=peer_public_key
        )
        changed = False
        if peer_endpoint is not None and link.peer_endpoint != peer_endpoint:
            if not link.peer_endpoint:
                raise ValueError(
                    "cannot set peer_endpoint on half-open link, use acknowledge_open_link instead"
                )
            link.peer_endpoint = peer_endpoint
            changed = True
        if peer_allowed_ips is not None and link.peer_allowed_ips != peer_allowed_ips:
            link.peer_allowed_ips = peer_allowed_ips
            changed = True
        if changed:
            self._save()
