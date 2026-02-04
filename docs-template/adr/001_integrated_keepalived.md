---
title: ADR-001 - Integrated keepalived
author: Weii Wang <weii.wang@canonical.com>
date: 2026-01-20
domain: architecture
replaced-by: 
---

# Integrated keepalived

## Context

Some subordinate charms, such as the hacluster charm and the keepalived
charm, can help install and set up VRRP on the WireGuard gateway charm.
This raises whether the WireGuard gateway charm should integrate
keepalived itself, or rely on other charms like the hacluster charm or
the keepalived charm to install and manage keepalived and VRRP.

## Decision

It has been decided that the WireGuard gateway charm should implement
keepalived internally instead of relying on a separate charm for it. The
reason is that the WireGuard gateway charm needs to configure special
VRRP scripts to adjust the weight of each unit based on the routes
present on each unit. This requires a dynamic and complex configuration
of the keepalived instance. If this needed to be delegated to another
charm, it would require implementing a new charm relation to convey the
configuration and updating the keepalived charm or hacluster charm to
support the new relation, which is too much work for this ad hoc task.

## Alternatives considered

Installation and configuration of keepalived and VRRP are delegated to a
separate charm such as the keepalived charm or the hacluster charm.

## Consequences

Need to implement the management of keepalived inside the WireGuard
gateway charm.
