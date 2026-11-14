---
myst:
  html_meta:
    "description lang=en": "Technical information related to the WireGuard gateway charm."
---

(reference)=

# Reference

Technical specifications and architectural details for the WireGuard gateway charm, covering the configuration options and actions that operators use to control it, the relation interfaces that connect it to peer gateways and observability tooling, and the internal design that routes encrypted traffic between sites.

## Configuration and operations

Operators drive the charm through its configuration options and actions, and the architecture reference explains how those settings translate into the running WireGuard, BIRD, and Keepalived processes that carry traffic.

```{toctree}
:hidden:
:maxdepth: 1

Configurations <configurations.md>
Actions <actions.md>
Charm architecture <charm-architecture.md>
```

## Connectivity and monitoring

A gateway becomes useful only once it is peered with other gateways and connected to a monitoring stack. Relation endpoints establish those links, and the charm exposes OSPF and routing metrics once traffic begins to flow.

```{toctree}
:hidden:
:maxdepth: 1

Integrations <integrations.md>
Metrics <metrics.md>
```
