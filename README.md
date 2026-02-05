# WireGuard gateway charm

[![CharmHub Badge](https://charmhub.io/wireguard-gateway/badge.svg)](https://charmhub.io/wireguard-gateway)
[![Publish to edge](https://github.com/canonical/wireguard-gateway-operator/actions/workflows/publish_charm.yaml/badge.svg)](https://github.com/canonical/wireguard-gateway-operator/actions/workflows/publish_charm.yaml)
[![Promote charm](https://github.com/canonical/wireguard-gateway-operator/actions/workflows/promote_charm.yaml/badge.svg)](https://github.com/canonical/wireguard-gateway-operator/actions/workflows/promote_charm.yaml)
[![Discourse Status](https://img.shields.io/discourse/status?server=https%3A%2F%2Fdiscourse.charmhub.io&style=flat&label=CharmHub%20Discourse)](https://discourse.charmhub.io)

A [Juju](https://juju.is/) [charm](https://documentation.ubuntu.com/juju/3.6/reference/charm/) deploying a highly available, high-performance site-to-site VPN based on WireGuard.

Like any Juju charm, this charm supports one-line deployment, configuration, integration, scaling, and more. For the Charmed WireGuard gateway, this includes:

* automatic WireGuard key exchange and interface management
* automatic route management and fault tolerance using OSPF on BIRD
* virtual redundant routing using VRRP on keepalived

For information about how to deploy, integrate, and manage this charm, see the official [WireGuard gateway documentation](./docs).

## Get started

To begin, refer to the [Getting Started](docs/tutorial.md) tutorial for step-by-step instructions.

### Basic operations

The charm supports customization, including:
- [Configuring `advertise-prefixes`](docs/how-to/config-advertise-prefixes.md)
- [Configuring virtual IPs](docs/how-to/config-vips.md)
- [Connecting to observability](docs/how-to/integrate-with-cos.md)

## Integrations

The WireGuard gateway charm has two relation interfaces, `wireguard-router-a` and `wireguard-router-b`, for peering with other WireGuard gateway charms. The two interfaces are equivalent, and a single relation between two WireGuard gateway charms is sufficient. For example, two WireGuard gateway charms can be deployed as follows:

```
juju switch wireguard-model-alpha
juju deploy wireguard-gateway wireguard-alpha
juju offer wireguard-alpha:wireguard-router-a

juju switch wireguard-model-beta
juju deploy wireguard-gateway wireguard-beta
juju consume controller:admin/wireguard-model-alpha.wireguard-alpha
juju deploy wireguard-gateway wireguard-beta
juju integrate wireguard-beta:wireguard-router-b wireguard-alpha
```

Apart from this required integration, the charm can be integrated with other Juju charms and services as well. You can find the full list of integrations in [the Charmhub documentation](https://charmhub.io/wireguard-gateway/integrations).

## Learn more

- [Read more](https://documentation.ubuntu.com/wireguard-gateway-charm/latest/)
- [Official webpage](https://www.wireguard.com/)
- [Troubleshooting](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)

## Project and community

The WordPress Operator is a member of the Ubuntu family. 
It's an open source project that warmly welcomes community projects, contributions, suggestions, fixes and constructive feedback.

- [Code of conduct](https://ubuntu.com/community/code-of-conduct)
- [Get support](https://discourse.charmhub.io/)
- [Contribute](CONTRIBUTING.md)
- [Matrix](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)

## Licensing and trademark

WireGuard gateway charm is licensed under the Apache License, Version 2.0 (Apache-2.0). WireGuard is a trademark of Jason A. Donenfeld. This project is not affiliated with the trademark owner. The name is used only to identify compatibility with WireGuard under fair use.
