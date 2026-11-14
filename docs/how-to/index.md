---
myst:
  html_meta:
    "description lang=en": "How-to guides covering the entire WireGuard gateway charm operations lifecycle."
---

(how_to)=

# How-to guides

Operate the WireGuard gateway charm across its lifecycle, from shaping the VPN routing, redundancy, and throughput of a freshly deployed gateway to keeping an established deployment observable and up to date. Each guide assumes that you have already deployed the charm with Juju.

## Networking and VPN configuration

A WireGuard gateway's core behavior is defined by charm configuration options that control which networks it routes to, how it fails over, and how much traffic it can sustain. Setting these correctly turns a deployed unit into a working, resilient tunnel endpoint.

```{toctree}
:hidden:
:maxdepth: 1

Set up a site-to-site VPN <setup-site-to-site-vpn.md>
Enable VRRP <enable-vrrp.md>
Tune performance on multi-core CPUs <performance-tuning.md>
```

## Operations and maintenance

Once a gateway is carrying traffic, keeping it healthy means watching its behavior, recovering lost units, adopting new revisions without interrupting service, and improving the guides that describe these tasks.

```{toctree}
:hidden:
:maxdepth: 1

Integrate with COS <integrate-with-cos.md>
Back up and restore <back-up-restore.md>
Upgrade <upgrade.md>
Contribute <contribute>
```
