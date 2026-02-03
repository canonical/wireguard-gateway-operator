---
title: ADR-000 - Use BIRD for the OSPF implementation
author: Weii Wang <weii.wang@canonical.com>
date: 2026-01-19
domain: architecture
replaced-by: 
---

# Use BIRD as the OSPF implementation

## Context

Currently, there are multiple implementations of OSPF in the Linux
landscape, including FRRouting and BIRD. Practically, they don't have
significant advantages over each other. FRR is in the Ubuntu main
archive, thus better maintained by the Ubuntu team. BIRD supports
RFC5838 address families in OSPFv3, allowing it to advertise IPv4 and
IPv6 in a single IPv6 OSPFv3 instance.

## Decision

In the end, BIRD is chosen as the implementation of OSPF in the
WireGuard gateway charm. This is to better align with the network team's
future plan and technical stack. Also, RFC5838 address families in
OSPFv3 are a good addition.

## Alternatives considered

FRRouting as the implementation of OSPF in the WireGuard gateway charm.

## Consequences

The BIRD configuration and management are implemented in the WireGuard
gateway charm.
