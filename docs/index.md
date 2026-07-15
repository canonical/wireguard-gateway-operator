---
myst:
  html_meta:
    "description lang=en": "A Juju charm deploying a highly available, high-performance site-to-site VPN based on WireGuard."
---

<!-- vale Canonical.007-Headings-sentence-case = NO -->

# WireGuard gateway operator

<!-- vale Canonical.007-Headings-sentence-case = YES -->

A [Juju](https://juju.is/) [charm](https://documentation.ubuntu.com/juju/3.6/reference/charm/) deploying a highly available, high-performance site-to-site VPN based on WireGuard.

Like any Juju charm, this charm supports one-line deployment, configuration, integration, scaling, and more. For the Charmed WireGuard gateway, this includes:

* Automatic WireGuard key exchange and interface management
* Automatic route management and fault tolerance using OSPF on BIRD
* Virtual redundant routing using VRRP on Keepalived

This charm will make operating highly available, high-performance site-to-site VPN simple and straightforward for DevOps or SRE teams through Juju's clean interface. 

## In this documentation

```{list-table}
   :header-rows: 1
   :widths: 15 30

* - 
  - 
* - **Get started**
  - {ref}`Deploy and peer two gateways <tutorial_index>`
* - **Operations**
  - {ref}`Back up and restore <how_to_back_up_restore>` | {ref}`Actions <reference_actions>` | {ref}`Configurations <reference_configurations>` | {ref}`Upgrade <how_to_upgrade>`
* - **Observability**
  - {ref}`Integrate with COS <how_to_integrate_with_cos>` | {ref}`Metrics <reference_metrics>`
* - **Design**
  - {ref}`Charm architecture <reference_charm_architecture>` | {ref}`WireGuard router peering <reference_integrations>`
* - **Security**
  - {ref}`Overview <explanation_security>`
```

## How this documentation is organized

This documentation uses the
[Diátaxis documentation structure](https://diataxis.fr/).

* The {ref}`Tutorial <tutorial_index>` takes you step-by-step through deploying and peering two WireGuard gateway charms.
* The {ref}`How-to guides <how_to>` cover practical tasks for integrating, maintaining, and upgrading your WireGuard gateway deployment.
* {ref}`Reference <reference>` provides technical details on the charm's actions, configurations, integrations, metrics, and architecture.
* {ref}`Explanation <explanation>` includes context and discussion of key topics, such as security.

## Contributing to this documentation

Documentation is an important part of this project, and we take the same open-source approach
to the documentation as the code. As such, we welcome community contributions, suggestions, and
constructive feedback on our documentation.
See {ref}`How to contribute <how_to_contribute>` for more information.


If there's a particular area of documentation that you'd like to see that's missing, please 
[file a bug](https://github.com/canonical/wireguard-gateway-operator/issues).

## Project and community

The WireGuard gateway operator is a member of the Ubuntu family. 
It's an open source project that warmly welcomes community projects, contributions, suggestions, fixes and constructive feedback.

- [Code of conduct](https://ubuntu.com/community/code-of-conduct)
- [Get support](https://discourse.charmhub.io/)
- {ref}`Contribute <how_to_contribute>`
- [Matrix](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)

Thinking about using the WireGuard gateway operator for your next project? 
[Get in touch](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)!


```{toctree}
:hidden:
Tutorial <tutorial>
how-to/index.md
reference/index.md
explanation/index.md
Changelog <changelog.md>
```
