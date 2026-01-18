#!/usr/bin/env python3

# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""WireGuard gateway charm service."""

import ipaddress
import logging
import pathlib
import typing

import ops

import relations
import wgdb
import wireguard
from wgdb import WireguardLinkStatus

logger = logging.getLogger(__name__)

_WGDB_DIR = pathlib.Path("/opt/wireguard-gateway/")
_WIREGUARD_ROUTER_PROVIDER_RELATION = "provide-wireguard-router"
_WIREGUARD_ROUTER_REQUIRER_RELATION = "require-wireguard-router"


def join_host_port(host: str, port: int) -> str:
    """Join host and port into a string:

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
        return f"{h}:{port}"
    else:
        if ip.version == 6:
            return f"[{h}]:{port}"
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

    def _create_wgdb(self):
        """Create WireGuard database if not exists."""
        file = _WGDB_DIR / f"{self.unit.name.replace('/', '-')}.json"
        file.parent.mkdir(parents=True, exist_ok=True)
        return wgdb.WireguardDb(file=file)

    def reconcile(self, event: ops.EventBase) -> None:
        """Reconcile callback."""
        self._reconcile()

    def _reconcile(self) -> None:
        """Holistic reconciliation method."""
        for relation in self.model.relations[_WIREGUARD_ROUTER_PROVIDER_RELATION]:
            self._reconcile_relation(relation, is_provider=True)
        for relation in self.model.relations[_WIREGUARD_ROUTER_REQUIRER_RELATION]:
            self._reconcile_relation(relation, is_provider=False)

    def _reconcile_relation(self, relation: ops.Relation, is_provider: bool) -> None:
        """Holistic reconciliation method for one relation."""
        data = relations.WireguardRouterRelation.from_relation(
            charm=self, relation=relation, is_provider=is_provider
        )
        self._relation_add_keys(data)
        self._relation_add_links(data)
        self._relation_update_links(data)
        self._relation_sync_db(data)

    def _relation_add_keys(self, relation: relations.WireguardRouterRelation) -> None:
        while len(self._wgdb.list_keys(relation.id)) < self.config.get("tunnels"):
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
                    self._wgdb.search_link(
                        public_key=key.public_key, peer_public_key=peer_key
                    )
                    for peer_key in unit.public_keys
                ):
                    continue
                # try to find a peer key that had not yet been used in a link with myself
                # and then form a link with that key
                for peer_key in unit.public_keys:
                    if any(
                        self._wgdb.search_link(
                            public_key=key.public_key, peer_public_key=peer_key
                        )
                        for key in self._wgdb.list_keys(relation.id)
                    ):
                        continue
                    port = self._wgdb.allocate_port()
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
                    link.peer_public_key == k.public_key
                    for k in self._wgdb.list_keys(relation.id)
                ):
                    # link is not for myself
                    continue
                half_open_link = self._wgdb.search_link(
                    link.peer_public_key, link.public_key
                )
                endpoint = join_host_port(unit.ingress_address, link.port)
                if not half_open_link:
                    port = self._wgdb.allocate_port()
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

    def _relation_update_links(
        self, relation: relations.WireguardRouterRelation
    ) -> None:
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
            if unit and listen_port:
                self._wgdb.update_link(
                    public_key=link.public_key,
                    peer_public_key=link.peer_public_key,
                    peer_endpoint=join_host_port(
                        unit.ingress_address, listen_port.port
                    ),
                    peer_allowed_ips=unit.advertise_prefixes,
                )
            match link.status:
                case WireguardLinkStatus.HALF_OPEN:
                    self._relation_update_half_open_link(relation=relation, link=link)
                case WireguardLinkStatus.OPEN:
                    self._relation_update_open_link(relation=relation, link=link)
                case WireguardLinkStatus.HALF_CLOSE:
                    self._relation_update_half_close_link(relation=relation, link=link)

    def _relation_update_half_open_link(
        self, relation: relations.WireguardRouterRelation, link: wgdb.WireguardLink
    ) -> None:
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
                    peer_endpoint=join_host_port(
                        unit.ingress_address, listen_port.port
                    ),
                )
                return

    def _relation_update_open_link(
        self, relation: relations.WireguardRouterRelation, link: wgdb.WireguardLink
    ) -> None:
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
        self._close_link_without_public_key(relation, link)
        self._close_link_without_listen_port(relation, link)

    def _close_link_without_public_key(
        self, relation: relations.WireguardRouterRelation, link: wgdb.WireguardLink
    ) -> None:
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
                acknowledged=False,
            )
            return

    def _relation_sync_db(self, relation: relations.WireguardRouterRelation) -> None:
        relation.set_public_key(
            [k.public_key for k in self._wgdb.list_keys(relation.id)]
        )
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


if __name__ == "__main__":  # pragma: nocover
    ops.main(Charm)
