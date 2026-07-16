(how_to_performance_tuning)=

# Performance tuning on multi-core CPUs

A single WireGuard VPN tunnel does not scale very well on multi-core CPUs, as
some of the WireGuard packet processing is done in a single thread. To improve
the performance of the WireGuard gateway charm, you can increase the `tunnels`
charm configuration option to increase throughput.

The `tunnels` setting determines how many WireGuard tunnels will be created for
each WireGuard gateway charm unit pair between any two units in the WireGuard
integration. Because a WireGuard gateway charm deployment may have multiple
units, the total number of tunnels that will be created on a WireGuard unit is
actually equal to `N(tunnels) x M(remote units)`. For this reason, we don't
recommend setting the `tunnels` value too high when you have a multi-unit
deployment.

Some other things need to be considered for the `tunnels` setting. Due to the
need for zero-downtime key rotation, the minimum number of tunnels is two, so
there will always be at least one active tunnel. Also, if the two WireGuard
deployments have different `tunnels` configurations, the effective number of
`tunnels` will be the lower of the two.
