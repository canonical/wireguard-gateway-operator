---
myst:
  html_meta:
    "description lang=en": "Learn how to set the advertised-prefixes configuration for the WireGuard gateway charm."
---

(how_to_decide_advertise_prefixes)=

# How to decide the advertised-prefixes configuration value for your deployment

The `advertise-prefixes` configuration of the WireGuard gateway charm
represents what network this WireGuard gateway unit is adjacent to and knows how
to route to.

For example, let's say we have two sites that need to be
connected with the WireGuard gateway charm:

 * Site A network has the IP address `10.0.0.0/8`.
 * Site B has the network IP address `192.168.0.0/16`.

Then the WireGuard gateway charm deployed on site A should have an
`advertise-prefixes` value of `10.0.0.0/8`, and site B's instance of the
WireGuard gateway charm should have an `advertise-prefixes` value of
`192.168.0.0/16`:


```{mermaid}
flowchart LR
    siteA["Site A (Network: 10.0.0.0/8)"]
    siteB["Site B (Network: 192.168.0.0/16)"]
    wireguardA["WireGuard gateway charm<br/>advertise-prefixes: 10.0.0.0/8"]
    wireguardB["WireGuard gateway charm<br/>advertise-prefixes: 192.168.0.0/16"]
    siteA --- wireguardA
    wireguardA <-->|WireGuard tunnel| wireguardB
    wireguardB --- siteB
```

The `advertise-prefixes` configuration allows the WireGuard gateway
charm unit to inform other integrated WireGuard gateway charm deployments
about the prefixes the unit is responsible for. The other integrated deployments
know to send all relevant network traffic to the unit.
