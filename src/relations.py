# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Relations module provider parser for relation data."""

import base64
import ipaddress

import ops
import pydantic
from pydantic import field_validator


class WireguardRouterListenPort(pydantic.BaseModel):
    """WireGuard router relation listen port data model."""

    model_config = pydantic.ConfigDict(
        frozen=True,
    )

    public_key: str
    peer_public_key: str
    port: int

    @field_validator("public_key", "peer_public_key")
    @classmethod
    def _validate_public_key(cls, v: str) -> str:
        if len(base64.b64decode(v)) != 32:
            raise ValueError("invalid WireGuard key")
        return v

    @field_validator("port")
    @classmethod
    def _validate_port(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError("port must be between 1 and 65535")
        return v


class WireguardRouterRelationData(pydantic.BaseModel):
    """WireGuard router relation data mode."""

    model_config = pydantic.ConfigDict(
        alias_generator=pydantic.AliasGenerator(
            alias=lambda n: n.replace("_", "-"),
        ),
        frozen=True,
    )
    ingress_address: str
    advertise_prefixes: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = pydantic.Field(
        default_factory=list
    )
    public_keys: list[str] = pydantic.Field(default_factory=list)
    listen_ports: list[WireguardRouterListenPort] = pydantic.Field(default_factory=list)

    @pydantic.field_serializer("advertise_prefixes")
    def _serialize_advertise_prefixes(
        self, value: list[ipaddress.IPv4Network | ipaddress.IPv6Network]
    ) -> str:
        return ", ".join(str(prefix) for prefix in value)

    @pydantic.field_validator("advertise_prefixes", mode="before")
    @classmethod
    def _validate_advertise_prefixes(
        cls, v: str
    ) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
        prefixes = []
        for item in v.split(","):
            prefix_str = item.strip()
            prefix = ipaddress.ip_network(prefix_str, strict=False)
            prefixes.append(prefix)
        return prefixes

    @pydantic.field_serializer("public_keys")
    def _serialize_public_keys(self, value: list[str]) -> str:
        return ",".join(value)

    @pydantic.field_validator("public_keys", mode="before")
    @classmethod
    def _validate_public_keys(cls, value: str) -> list[str]:
        keys = []
        for key in value.split(","):
            key = key.strip()
            if len(base64.b64decode(key)) != 32:
                raise ValueError("invalid WireGuard key")
            keys.append(key)
        return keys

    @pydantic.field_serializer("listen_ports")
    def _serialize_listen_ports(self, value: list[WireguardRouterListenPort]) -> str:
        return ",".join(":".join([p.public_key, p.peer_public_key, str(p.port)]) for p in value)

    @pydantic.field_validator("listen_ports", mode="before")
    @classmethod
    def _validate_listen_ports(cls, v: str) -> list[WireguardRouterListenPort]:
        ports = []
        for item in v.split(","):
            public_key, peer_public_key, port_str = item.strip().split(":")
            ports.append(
                WireguardRouterListenPort(
                    public_key=public_key,
                    peer_public_key=peer_public_key,
                    port=int(port_str),
                )
            )
        return ports

    @pydantic.model_validator(mode="after")
    def _validate_model(self) -> "WireguardRouterRelationData":
        for listen in self.listen_ports:
            if listen.public_key not in self.public_keys:
                raise ValueError("listen-ports public key not in public-keys")
        return self

    def lookup_listen_port(
        self, public_key: str, peer_public_key: str
    ) -> WireguardRouterListenPort | None:
        """Lookup listen port for given public key and peer public key.

        Args:
            public_key: The public key.
            peer_public_key: The peer public key.

        Returns:
            Listen port if found, None otherwise.
        """
        for port in self.listen_ports:
            if port.public_key == public_key and port.peer_public_key == peer_public_key:
                return port
        return None


class WireguardRouterRelation:
    """Wireguard router relation provider parser."""

    def __init__(
        self,
        unit: ops.Unit,
        relation: ops.Relation,
        is_provider: bool,
        data: WireguardRouterRelationData,
        remote_data: list[WireguardRouterRelationData],
    ) -> None:
        """Initialize the relation parser.

        Args:
            unit: The relation unit (self).
            relation: The relation instance.
            is_provider: Whether this unit is the provider of the relation.
            data: The relation data (self).
            remote_data: Remote unit date.
        """
        self._unit = unit
        self._relation = relation
        self._is_provider = is_provider
        self._data = data
        self._remote_data = remote_data

    @property
    def is_provider(self) -> bool:
        """Check if this unit is the provider of the relation.

        Return:
            True if this unit is the provider, False otherwise.
        """
        return self._is_provider

    @property
    def id(self) -> int:
        """Get the relation ID.

        Return:
            The relation ID.
        """
        return self._relation.id

    @property
    def remote_data(self) -> list[WireguardRouterRelationData]:
        """Get the remote units relation data.

        Returns:
            The remote units relation data.
        """
        return list(self._remote_data)

    def search_unit(self, *, public_key: str) -> WireguardRouterRelationData | None:
        """Search for a remote unit by public key.

        Args:
            public_key: The public key to search for.
        """
        for data in self._remote_data:
            if public_key in data.public_keys:
                return data
        return None

    @classmethod
    def from_relation(
        cls, charm: ops.CharmBase, relation: ops.Relation, is_provider: bool
    ) -> "WireguardRouterRelation":
        """Parse relation data from a WireGuard router relation.

        Args:
            charm: The charm instance.
            relation: The relation instance.
            is_provider: Whether this unit is the provider side of the relation.

        Returns:
            A new relation data object.
        """
        local_data = WireguardRouterRelationData.model_validate(relation.data[charm.unit])
        remote_data = []
        for unit in relation.units:
            remote_data.append(WireguardRouterRelationData.model_validate(relation.data[unit]))
        return cls(
            unit=charm.unit,
            relation=relation,
            is_provider=is_provider,
            data=local_data,
            remote_data=remote_data,
        )

    def _save(self) -> None:
        """Save the relation data back to the relation."""
        self._relation.data[self._unit].update(
            self._data.model_dump(exclude={"ingress_address", "ingress-address"}, by_alias=True)
        )

    def set_advertise_prefixes(
        self, advertise_prefixes: list[ipaddress.IPv4Network | ipaddress.IPv6Network]
    ) -> None:
        """Set the advertise-prefixes in the relation data.

        Args:
            advertise_prefixes: List of advertise prefixes.
        """
        self._data = self._data.model_copy(update={"advertise_prefixes": advertise_prefixes})
        self._save()

    def set_public_keys(self, public_keys: list[str]) -> None:
        """Set the public keys in the relation data.

        Args:
            public_keys: The public keys.
        """
        self._data = self._data.model_copy(update={"public_keys": public_keys})
        self._save()

    def set_listen_ports(self, listen_ports: list[WireguardRouterListenPort]) -> None:
        """Set the listen ports in the relation data.

        Args:
            listen_ports: The listen ports.
        """
        self._data = self._data.model_copy(update={"listen_ports": listen_ports})
        self._save()
