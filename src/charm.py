#!/usr/bin/env python3

# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""WireGuard gateway charm service."""

import ipaddress
import logging
import pathlib
import typing

import ops

import bird
import relations
import wgdb
import wireguard

logger = logging.getLogger(__name__)

WGDB_DIR = pathlib.Path("/opt/wireguard-gateway/")
WIREGUARD_ROUTER_PROVIDER_RELATION = "wireguard-router-a"
WIREGUARD_ROUTER_REQUIRER_RELATION = "wireguard-router-b"


class InvalidRelationDataError(Exception):
    """Invalid relation data."""


class InvalidConfigError(Exception):
    """Invalid configuration."""


def join_host_port(host: str, port: int) -> str:
    """Join host and port into a string.

    Args:
        host: Hostname or IP address.
        port: Port number.

    Returns:
        Joined host:port string.
    """
    h = host.strip()
    if h.startswith("[") and h.endswith("]"):
        return f"{h}:{port}"
    try:
        ip = ipaddress.ip_address(h)
    except ValueError:
        # it's domain name
        return f"{h}:{port}"
    else:
        if ip.version == 6:
            # it's a ipv6 address
            return f"[{h}]:{port}"
        # it's a ipv4 address
        return f"{h}:{port}"


class Charm(ops.CharmBase):
    """WireGuard gateway charm service."""

    def __init__(self, *args: typing.Any):
        """Construct.

        Args:
            args: Arguments passed to the CharmBase parent constructor.
        """
        super().__init__(*args)
        self._wgdb = self._create_wgdb()
        self.framework.observe(self.on.config_changed, self.reconcile)
        self.framework.observe(self.on.upgrade_charm, self.reconcile)
        self.framework.observe(self.on.update_status, self.reconcile)
        for relation in [
            WIREGUARD_ROUTER_PROVIDER_RELATION,
            WIREGUARD_ROUTER_REQUIRER_RELATION,
        ]:
            self.framework.observe(self.on[relation].relation_changed, self.reconcile)
            self.framework.observe(self.on[relation].relation_joined, self.reconcile)
            self.framework.observe(self.on[relation].relation_departed, self.reconcile)
            self.framework.observe(self.on[relation].relation_broken, self.reconcile)

    def _create_wgdb(self) -> wgdb.WireguardDb:
        """Create WireGuard database if not exists."""
        file = WGDB_DIR / f"{self.unit.name.replace('/', '-')}.json"
        file.parent.mkdir(parents=True, exist_ok=True)
        return wgdb.WireguardDb(file=file)

    def get_advertise_prefixes(
        self,
    ) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
        """Get advertise-prefixes configuration.

        Returns:
            List of advertise prefixes.
        """
        prefixes = []
        config = self.config.get("advertise-prefixes")
        if not config:
            config = ""
        for prefix in str(config).split(","):
            prefix = prefix.strip()
            if not prefix:
                continue
            try:
                prefixes.append(ipaddress.ip_network(prefix, strict=False))
            except ValueError:
                raise InvalidConfigError(
                    f"invalid advertise-prefixes: '{prefix}' is not a ipv4 or ipv6 prefix"
                )
        if not prefixes:
            raise InvalidConfigError("no advertise-prefixes configured")
        return prefixes

    def get_number_of_tunnels(self) -> int:
        """Get number of tunnels configuration.

        Returns:
            Number of tunnels.
        """
        val = self.config.get("tunnels")
        if val is None:
            raise ValueError("tunnels configuration is missing")
        tunnels = int(val)
        if tunnels <= 1:
            raise ValueError("tunnels configuration must be greater than 1")
        return tunnels

    def reconcile(self, event: ops.EventBase) -> None:
        """Reconcile the charm.

        Args:
            event: Event.
        """
        try:
            self._reconcile()
            advertise_prefixes = ", ".join(map(str, self.get_advertise_prefixes()))
            self.unit.status = ops.ActiveStatus(f"advertising prefixes: {advertise_prefixes}")
        except InvalidRelationDataError as exc:
            self.unit.status = ops.BlockedStatus(str(exc))
        except InvalidConfigError as exc:
            self.unit.status = ops.BlockedStatus(str(exc))

    def _reconcile(self) -> None:
        """Holistic reconciliation method."""
        advertise_prefixes = self.get_advertise_prefixes()
        self.get_number_of_tunnels()

        wireguard.wireguard_install()
        bird.bird_install()

        invalid_relations = []
        relation_is_provider = {}

        for relation_name in (
            WIREGUARD_ROUTER_PROVIDER_RELATION,
            WIREGUARD_ROUTER_REQUIRER_RELATION,
        ):
            for relation in self.model.relations[relation_name]:
                is_provider = relation_name == WIREGUARD_ROUTER_PROVIDER_RELATION
                relation_is_provider[relation.id] = is_provider
                try:
                    self._reconcile_relation(relation, is_provider=is_provider)
                except InvalidRelationDataError:
                    logger.exception("invalid relation date in relation id %s", relation.id)
                    invalid_relations.append(relation)

        removed_relations = [i for i in self._wgdb.list_owners() if i not in relation_is_provider]
        for removed_relation in removed_relations:
            self._relation_removed(removed_relation)

        self._open_ports()
        bird.bird_apply_db(db=self._wgdb, advertise_prefixes=advertise_prefixes)
        wireguard.wireguard_apply_db(self._wgdb, relation_is_provider)
        if invalid_relations:
            raise InvalidRelationDataError(
                f"relation(s) contains invalid data: {invalid_relations}"
            )

    def _reconcile_relation(self, relation: ops.Relation, is_provider: bool) -> None:
        """Holistic reconciliation method for one relation."""
        try:
            data = relations.WireguardRouterRelation.from_relation(
                charm=self,
                relation=relation,
                is_provider=is_provider,
            )
        except ValueError as exc:
            raise InvalidRelationDataError() from exc
        self._relation_add_keys(data)
        self._relation_add_links(data)
        self._relation_update_links(data)
        self._relation_sync(data)

    def _relation_add_keys(self, relation: relations.WireguardRouterRelation) -> None:
        while len(self._wgdb.list_keys(relation.id)) < self.get_number_of_tunnels():
            keypair = wireguard.generate_keypair()
            self._wgdb.add_key(
                owner=relation.id,
                public_key=keypair.public_key,
                private_key=keypair.private_key,
            )

    def _relation_add_links(self, relation: relations.WireguardRouterRelation) -> None:
        for unit in relation.remote_data:
            # initiate new links
            for key in self._wgdb.list_keys(relation.id):
                # requirer side don't initiate links
                if not relation.is_provider:
                    continue
                # if the key has been used in a link with that remote unit, skip it
                if any(
                    self._wgdb.search_link(public_key=key.public_key, peer_public_key=peer_key)
                    for peer_key in unit.public_keys
                ):
                    continue
                # try to find a peer key that had not yet been used in a link with myself
                # and then form a link with that key
                for peer_key in unit.public_keys:
                    if any(
                        self._wgdb.search_link(public_key=key.public_key, peer_public_key=peer_key)
                        for key in self._wgdb.list_keys(relation.id)
                    ):
                        continue
                    port = self._wgdb.allocate_port(relation.is_provider)
                    self._wgdb.open_link(
                        owner=relation.id,
                        public_key=key.public_key,
                        port=port,
                        peer_public_key=peer_key,
                        allowed_ips=unit.advertise_prefixes,
                    )
                    break
            # acknowledge incoming links
            for link in unit.listen_ports:
                if not any(
                    link.peer_public_key == k.public_key for k in self._wgdb.list_keys(relation.id)
                ):
                    # link is not for myself
                    continue
                half_open_link = self._wgdb.search_link(link.peer_public_key, link.public_key)
                endpoint = join_host_port(unit.ingress_address, link.port)
                if not half_open_link:
                    port = self._wgdb.allocate_port(relation.is_provider)
                    self._wgdb.open_link(
                        owner=relation.id,
                        public_key=link.peer_public_key,
                        port=port,
                        peer_public_key=link.public_key,
                        allowed_ips=unit.advertise_prefixes,
                        peer_endpoint=endpoint,
                    )
                else:
                    self._wgdb.acknowledge_open_link(
                        public_key=link.peer_public_key,
                        peer_public_key=link.public_key,
                        peer_endpoint=endpoint,
                    )

    def _relation_update_links(self, relation: relations.WireguardRouterRelation) -> None:
        for link in self._wgdb.list_link(owner=relation.id, include_half_closed=True):
            unit = relation.search_unit(public_key=link.peer_public_key)
            listen_port = (
                unit.lookup_listen_port(
                    public_key=link.peer_public_key,
                    peer_public_key=link.public_key,
                )
                if unit
                else None
            )
            # update the endpoint and advertise-prefixes in case they changed
            if unit and listen_port:
                self._wgdb.update_link(
                    public_key=link.public_key,
                    peer_public_key=link.peer_public_key,
                    peer_endpoint=join_host_port(unit.ingress_address, listen_port.port),
                    peer_allowed_ips=unit.advertise_prefixes,
                )
            # update link state
            match link.status:
                case wgdb.WireguardLinkStatus.HALF_OPEN:
                    self._relation_update_half_open_link(relation=relation, link=link)
                case wgdb.WireguardLinkStatus.OPEN:
                    self._relation_update_open_link(relation=relation, link=link)
                case wgdb.WireguardLinkStatus.HALF_CLOSE:
                    self._relation_update_half_close_link(relation=relation, link=link)

    def _relation_update_half_open_link(
        self, relation: relations.WireguardRouterRelation, link: wgdb.WireguardLink
    ) -> None:
        """Update a half-open WireGuard link.

        Transitions:
          - half-open -> closed:
              - The peer public key is no longer present in the remote `public-keys` field.
          - half-open -> open:
              - The remote unit acknowledges the link by advertising it in the `listen-port` field.
        """
        self._close_link_without_public_key(relation, link)

        for unit in relation.remote_data:
            for listen_port in unit.listen_ports:
                if (
                    listen_port.peer_public_key != link.public_key
                    or listen_port.public_key != link.peer_public_key
                ):
                    continue
                self._wgdb.acknowledge_open_link(
                    public_key=link.public_key,
                    peer_public_key=link.peer_public_key,
                    peer_endpoint=join_host_port(unit.ingress_address, listen_port.port),
                )
                return

    def _relation_update_open_link(
        self, relation: relations.WireguardRouterRelation, link: wgdb.WireguardLink
    ) -> None:
        """Update an open WireGuard link.

        Transitions:
          - open -> closed:
              - The peer public key is no longer present in the remote `public-keys` field.
              - The link is no longer present in the remote `listen-port` field.
          - open -> half-close:
              - The link's corresponding public key is retired.
        """
        self._close_link_without_public_key(relation, link)
        self._close_link_without_listen_port(relation, link)

        key = self._wgdb.search_key(public_key=link.public_key)
        if key.retired:
            self._wgdb.close_link(
                public_key=link.public_key,
                peer_public_key=link.peer_public_key,
            )

    def _relation_update_half_close_link(
        self, relation: relations.WireguardRouterRelation, link: wgdb.WireguardLink
    ) -> None:
        """Update a half-close WireGuard link.

        Transitions:
          - half-close -> closed:
              - The peer public key is no longer present in the remote `public-keys` field.
              - The link is no longer present in the remote `listen-port` field.
        """
        self._close_link_without_public_key(relation, link)
        self._close_link_without_listen_port(relation, link)

    def _close_link_without_public_key(
        self, relation: relations.WireguardRouterRelation, link: wgdb.WireguardLink
    ) -> None:
        """Close link if the peer public key of the link no longer exists in the remote relation."""
        remote_public_keys = []
        for unit in relation.remote_data:
            remote_public_keys.extend(unit.public_keys)

        if link.peer_public_key not in remote_public_keys:
            self._wgdb.close_link(
                public_key=link.public_key,
                peer_public_key=link.peer_public_key,
                acknowledged=True,
            )
            return

    def _close_link_without_listen_port(
        self, relation: relations.WireguardRouterRelation, link: wgdb.WireguardLink
    ) -> None:
        """Close link if the link no longer exists in the remote relation's listen-ports field."""
        found = False
        for unit in relation.remote_data:
            for listen_port in unit.listen_ports:
                if (
                    listen_port.peer_public_key == link.public_key
                    and listen_port.public_key == link.peer_public_key
                ):
                    found = True
        if not found:
            self._wgdb.close_link(
                public_key=link.public_key,
                peer_public_key=link.peer_public_key,
                acknowledged=True,
            )
            return

    def _relation_sync(self, relation: relations.WireguardRouterRelation) -> None:
        """Write the WireGuard database data back to the relation."""
        relation.set_advertise_prefixes(self.get_advertise_prefixes())
        relation.set_public_keys([k.public_key for k in self._wgdb.list_keys(relation.id)])
        relation.set_listen_ports(
            [
                relations.WireguardRouterListenPort(
                    public_key=link.public_key,
                    peer_public_key=link.peer_public_key,
                    port=link.port,
                )
                for link in self._wgdb.list_link(relation.id)
            ]
        )

    def _relation_removed(self, relation_id: int) -> None:
        """Cleanup on relation broken."""
        for key in self._wgdb.list_keys(relation_id):
            self._wgdb.retire_key(key.public_key)

        for link in self._wgdb.list_link(relation_id, include_half_closed=True):
            self._wgdb.close_link(
                public_key=link.public_key,
                peer_public_key=link.peer_public_key,
                acknowledged=True,
            )

    def _open_ports(self):
        """Open the WireGuard ports."""
        ports = []
        for link in self._wgdb.list_link(include_half_closed=True):
            ports.append(ops.Port(protocol="udp", port=link.port))
        self.unit.set_ports(*ports)


if __name__ == "__main__":  # pragma: nocover
    ops.main(Charm)
