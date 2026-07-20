---
myst:
  html_meta:
    "description lang=en": "Learn how to enable Virtual Router Redundancy Protocol for the WireGuard gateway charm."
---

(how_to_enable_vrrp)=

# How to enable VRRP

VRRP (Virtual Router Redundancy Protocol) is a network redundancy protocol that
provides high availability for the WireGuard gateway. The WireGuard gateway
charm supports VRRP through the embedded `keepalived`. You can enable the VRRP
feature by setting the VIP (virtual IP address) in the `vips` charm
configuration.

The `vips` configuration accepts a list of IPv4 or IPv6 network addresses, for
example, `10.0.0.1/24` or `2001:db8::1/32`, representing the virtual IP address
and VRRP subnet. When this configuration is set, the WireGuard gateway charm
will enable VRRP using the specified VIP address on the network interfaces
associated with the VIP address.

For example, if you have the following WireGuard gateway deployment:

```{terminal}
:output-only:

Model           Controller  Cloud/Region         Version  SLA          Timestamp
test-wireguard  lxd         localhost/localhost  3.6.25   unsupported  01:40:27+08:00

App                Version  Status  Scale  Charm              Channel      Rev  Exposed  Message
wireguard-gateway           active      2  wireguard-gateway  latest/edge   12  no       advertising prefixes: 10.0.0.0/8

Unit                  Workload  Agent  Machine  Public address  Ports  Message
wireguard-gateway/0*  active    idle   0        10.240.160.10          advertising prefixes: 10.0.0.0/8
wireguard-gateway/1   active    idle   1        10.240.160.189         advertising prefixes: 10.0.0.0/8

Machine  State    Address         Inst id        Base          AZ           Message
0        started  10.240.160.10   juju-40e6d0-0  ubuntu@24.04  work-laptop  Running
1        started  10.240.160.189  juju-40e6d0-1  ubuntu@24.04  work-laptop  Running
```

You can set the `vips` configuration option to `10.240.160.111/24`, and then you
should be able to access the WireGuard gateway using the VIP address. Traffic
destined for the VIP will be routed to a healthy WireGuard gateway unit, thus
providing high availability.
