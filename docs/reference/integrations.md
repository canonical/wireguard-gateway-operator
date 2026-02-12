(reference_integrations)=

# Integrations

<!-- vale Canonical.007-Headings-sentence-case = NO -->

## WireGuard router integration

<!-- vale Canonical.007-Headings-sentence-case = YES -->

_Interface_: `wireguard-router-a`
_Supported charms_: WireGuard gateway charms

The WireGuard gateway charm uses the `wireguard-router-a` relation to integrate with another WireGuard gateway charm for network peering. The `wireguard-router-a` and `wireguard-router-b` relations are equivalent.

Example `wireguard-router-a` integrate command: 

```
juju integrate wireguard-gateway-a:wireguard-router-a wireguard-gateway-b:wireguard-router-b
```

_Interface_: `wireguard-router-b`
_Supported charms_: WireGuard gateway charms

The WireGuard gateway charm uses the `wireguard-router-b` relation to integrate with another WireGuard gateway charm for network peering. The `wireguard-router-a` and `wireguard-router-b` relations are equivalent.

Example `wireguard-router-b` integrate command: 

```
juju integrate wireguard-gateway-b:wireguard-router-b wireguard-gateway-a:wireguard-router-a
```

# COS agent integration

_Interface_: `cos-agent`
_Supported charms_: [OpenTelemetry collector charm](https://charmhub.io/opentelemetry-collector), [Grafana agent charm](https://charmcraft.io/grafana-agent)

The WireGuard gateway charm uses the `cos-agent` relation to integrate with COS agent subordinate charms like the OpenTelemetry collector charm to provide COS integration, which provides you metrics, logs, and dashboards.

Example `cos-agent` integrate command: 

```
juju integrate wireguard-gateway:cos-agent opentelemetry-collector
```
