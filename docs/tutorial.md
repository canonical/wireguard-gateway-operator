---
myst:
  html_meta:
    "description lang=en": "The WireGuard gateway charm tutorial that walks a user through a basic WireGuard gateway deployment."
---

(tutorial_index)=

<!-- vale Canonical.007-Headings-sentence-case = NO -->
# Deploy the WireGuard gateway charm for the first time
<!-- vale Canonical.007-Headings-sentence-case = YES -->

The `wireguard-gateway` charm helps you deploy a high-performance, highly available WireGuard site-to-site VPN. This tutorial will walk you through each step to create a basic WireGuard gateway deployment with two WireGuard gateway charms.

## What you'll do

1. Deploy [WireGuard gateway charms](https://charmhub.io/wireguard-gateway)
2. Peering between two WireGuard gateway charms
3. Test the routing
4. Clean up the environment

## What you'll need

You will need a working station, e.g., a laptop, with AMD64 architecture. Your working station
should have at least 4 CPU cores, 8 GB of RAM, and 50 GB of disk space.

````{tip}
You can use Multipass to create an isolated environment by running:
```
multipass launch 24.04 --name charm-tutorial-vm --cpus 4 --memory 8G --disk 50G
```
````

This tutorial requires the following software to be installed on your working station
(either locally or in the Multipass VM):

- Juju 3
- MicroK8s 1.33

Use [Concierge](https://github.com/canonical/concierge) to set up Juju and MicroK8s:

```
sudo snap install --classic concierge
sudo concierge prepare -p lxd
```

This first command installs Concierge, and the second command uses Concierge to install
and configure Juju and LXD.

For this tutorial, Juju must be bootstrapped to a LXD controller. Concierge should
complete this step for you, and you can verify by checking for `msg="Bootstrapped Juju" provider=lxd`
in the terminal output and by running `juju controllers`.

If Concierge did not perform the bootstrap, run:

```
juju bootstrap lxd tutorial-controller
```

To be able to work inside the Multipass VM, log in with the following command:

```bash
multipass shell charm-tutorial-vm 
```

```{note}
If you're working locally, you don't need to do this step.
```

## Set up the environment

To manage resources effectively and to separate this tutorial's workload from
your usual work, create a new model in the MicroK8s controller using the following command:

```
juju add-model wireguard-tutorial
```

<!-- vale Canonical.007-Headings-sentence-case = NO -->
## Deploy WireGuard gateway charms
<!-- vale Canonical.007-Headings-sentence-case = YES -->

Start off by deploying two WireGuard gateway charm. By default it will deploy the latest stable release of
the `wireguard-gateway` charm.

```
juju deploy wireguard-gateway wireguard-a
juju deploy wireguard-gateway wireguard-b
```

## Peering between two WireGuard gateway charms 

Now we need to integrate the two WireGuard gateway charms using the `wireguard-route-a` and `wireguard-router-b` relation {ref}`interface <juju:relation>` so they will establish WireGuard tunnels and forward network packets between them. `wireguard-route-a` and `wireguard-router-b` are interchangeable, so you can pick either of them. In this example we will use `wireguard-router-a` on the `wireguard-a` charm and the `wireguard-route-b` relation interface on the `wireguard-b` charm to connect them together.

```
juju integrate wireguard-a:wireguard-router-a wireguard-b:wireguard-router-b
```

Run `juju status` to check the current status of the deployment. The output should be similar to the following:

```{terminal}
:output-only:

Model               Controller  Cloud/Region         Version  SLA          Timestamp
wireguard-tutorial  lxd         localhost/localhost  3.6.11   unsupported  16:42:44+08:00

App          Version  Status   Scale  Charm              Channel  Rev  Exposed  Message
wireguard-a           blocked      1  wireguard-gateway             0  no       no advertise-prefixes configured
wireguard-b           blocked      1  wireguard-gateway             1  no       no advertise-prefixes configured

Unit            Workload  Agent      Machine  Public address  Ports            Message
wireguard-a/0*  active    idle       0        10.212.71.231   50001,50003/udp  advertising prefixes: 192.0.2.0/24
wireguard-b/0*  active    idle       1        10.212.71.52    50000,50002/udp  advertising prefixes: 198.51.100.0/24

Machine  State    Address        Inst id        Base          AZ           Message
0        started  10.212.71.231  juju-fc22ca-0  ubuntu@24.04  workstation  Running
1        started  10.212.71.52   juju-fc22ca-1  ubuntu@24.04  workstation  Running
```

It’s showing “blocked” for both WireGuard gateway charms. This is normal, and we’ll configure `advertise-prefixes` in the next step.

## Test the routing

In this test scenario, we will create two test network regions, `192.0.2.0/24` and `198.51.100.0/24`, and the purpose of the WireGuard gateway charms is to connect these two network regions together. Let's assign `wireguard-a` to be on the `192.0.2.0/24` network side, and `wireguard-b` to be on the `198.51.100.0/24` network side. To achieve this, set the `advertise-prefixes` configuration on the WireGuard gateway charms. You can basically imagine this configuration as the networks this charm instance can reach.

```
juju config wireguard-a advertise-prefixes=192.0.2.0/24
juju config wireguard-b advertise-prefixes=198.51.100.0/24
```

Run `juju status` to check the current status of the deployment. The output should be similar to the following, showing all charms active:

```{terminal}
:output-only:

Model               Controller  Cloud/Region         Version  SLA          Timestamp
wireguard-tutorial  lxd         localhost/localhost  3.6.11   unsupported  16:54:48+08:00

App          Version  Status  Scale  Charm              Channel  Rev  Exposed  Message
wireguard-a           active      1  wireguard-gateway             0  no       advertising prefixes: 192.0.2.0/24
wireguard-b           active      1  wireguard-gateway             1  no       advertising prefixes: 198.51.100.0/24

Unit            Workload  Agent  Machine  Public address  Ports  Message
wireguard-a/0*  active    idle   0        10.212.71.231          advertising prefixes: 192.0.2.0/24
wireguard-b/0*  active    idle   1        10.212.71.52           advertising prefixes: 198.51.100.0/24

Machine  State    Address        Inst id        Base          AZ           Message
0        started  10.212.71.231  juju-fc22ca-0  ubuntu@24.04  workstation  Running
1        started  10.212.71.52   juju-fc22ca-1  ubuntu@24.04  workstation  Running
```

Now let's create two test machines using the [Ubuntu charm](https://charmhub.io/ubuntu) to deploy them in the two test network regions: `test-a` in `192.0.2.0/24` and `test-b` in `198.51.100.0/24`.

```
juju deploy ubuntu test-a
juju deploy ubuntu test-b
```

Next, let's assign IP addresses to these machines within their designated network ranges.

```
juju exec --unit wireguard-a/0 sudo ip addr add 192.0.2.1/24 dev eth0
juju exec --unit test-a/0 sudo ip addr add 192.0.2.2/24 dev eth0
juju exec --unit wireguard-b/0 sudo ip addr add 198.51.100.1/24 dev eth0
juju exec --unit test-b/0 sudo ip addr add 198.51.100.2/24 dev eth0
```

<!-- vale Canonical.025a-latinisms-with-english-equivalents = NO -->
Now add routes on the `test-a` to route all traffic to `198.51.100.0/24` via `wireguard-a` and on the `test-b` to route all traffic to `192.0.2.0/24` via `wireguard-b`.
<!-- vale Canonical.025a-latinisms-with-english-equivalents = YES -->

```
juju exec --unit test-a/0 sudo ip route add 198.51.100.0/24 via 192.0.2.1
juju exec --unit test-b/0 sudo ip route add 192.0.2.0/24 via 198.51.100.1
```

Now we can validate routing by running a simple ping command. We use the `-I 192.0.2.2` parameter here to select the source IP address for the ping packet, so that the source IP is within the range of the two test networks we set up and the return path is clear.

```
juju exec --unit test-a/0 -- ping 198.51.100.2 -I 192.0.2.2 -c 5
```

From the ping command results, the packet is successfully sent by the `test-a` machine to the `wireguard-a` machine, then forwarded to the `wireguard-b` machine. The `wireguard-b` machine then forwards the packet to the `test-b` machine. The ping reply packet travels along the same path in reverse, from `test-b` to `wireguard-b` to `wireguard-a` to `test-a`.

```{terminal}
:output-only:

PING 198.51.100.2 (198.51.100.2) from 192.0.2.2 : 56(84) bytes of data.
64 bytes from 198.51.100.2: icmp_seq=1 ttl=62 time=0.196 ms
64 bytes from 198.51.100.2: icmp_seq=2 ttl=62 time=0.198 ms
64 bytes from 198.51.100.2: icmp_seq=3 ttl=62 time=0.236 ms
64 bytes from 198.51.100.2: icmp_seq=4 ttl=62 time=0.284 ms
64 bytes from 198.51.100.2: icmp_seq=5 ttl=62 time=0.277 ms

--- 198.51.100.2 ping statistics ---
5 packets transmitted, 5 received, 0% packet loss, time 4129ms
rtt min/avg/max/mdev = 0.196/0.238/0.284/0.037 ms
```

## Clean up the environment

Congratulations! You successfully deployed the WireGuard gateway charm.

You can clean up your environment by following this guide:
{ref}`Tear down your test environment <juju:tear-things-down>`
