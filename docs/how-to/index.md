---
myst:
  html_meta:
    "description lang=en": "How-to guides covering the entire WireGuard gateway charm operations lifecycle."
---

(how_to)=

# How-to guides

Operate the WireGuard gateway charm across its lifecycle, from shaping the VPN routing, redundancy, and throughput of a freshly deployed gateway to keeping an established deployment observable and up to date. Each guide assumes that you have already deployed the charm with Juju.

## Networking and VPN configuration

A WireGuard gateway's core behavior is defined by a handful of charm configuration options that control which networks it routes to, how it fails over, and how much traffic it can sustain. Setting these correctly turns a deployed unit into a working, resilient tunnel endpoint.

* [Set up a site-to-site VPN]
* [Enable VRRP]
* [Tune performance on multi-core CPUs]

## Operations and maintenance

Once a gateway is carrying traffic, keeping it healthy means watching its behavior, recovering lost units, and adopting new revisions without interrupting service -- and, when you spot a gap, improving the guides that describe these tasks.

* [Integrate with COS]
* [Back up and restore]
* [Upgrade]
* [Contribute]

<!--Links-->
[Set up a site-to-site VPN]: setup-site-to-site-vpn.md
[Enable VRRP]: enable-vrrp.md
[Tune performance on multi-core CPUs]: performance-tuning.md
[Integrate with COS]: integrate-with-cos.md
[Back up and restore]: back-up-restore.md
[Upgrade]: upgrade.md
[Contribute]: contribute.rst

```{toctree}
:hidden:

Set up a site-to-site VPN <setup-site-to-site-vpn.md>
Enable VRRP <enable-vrrp.md>
Tune performance on multi-core CPUs <performance-tuning.md>
Integrate with COS <integrate-with-cos.md>
Back up and restore <back-up-restore.md>
Upgrade <upgrade.md>
Contribute <contribute>
```
