---
myst:
  html_meta:
    "description lang=en": "The WireGuard gateway charm tutorial that walks a user through a basic WireGuard gateway deployment."
---

(tutorial_index)=

# Deploy the WireGuard gateway charm for the first time

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

## Deploy WireGuard gateway charms

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
Model               Controller  Cloud/Region         Version  SLA          Timestamp
wireguard-tutorial  lxd         localhost/localhost  3.6.11   unsupported  16:42:44+08:00

App          Version  Status   Scale  Charm              Channel  Rev  Exposed  Message
wireguard-a           blocked      1  wireguard-gateway             0  no       no advertise-prefixes configured
wireguard-b           blocked      1  wireguard-gateway             1  no       no advertise-prefixes configured

Unit            Workload  Agent  Machine  Public address  Ports  Message
wireguard-a/0*  blocked   idle   0        10.212.71.231          no advertise-prefixes configured
wireguard-b/0*  blocked   idle   1        10.212.71.52           no advertise-prefixes configured

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

Now add routes on the `test-a` to route all traffic to `198.51.100.0/24` via `wireguard-a` and on the `test-b` to route all traffic to `192.0.2.0/24` via `wireguard-b`.

```
juju exec --unit test-a/0 sudo ip route add 198.51.100.0/24 via 192.0.2.1
juju exec --unit test-b/0 sudo ip route add 192.0.2.0/24 via 198.51.100.1
```

## Clean up the environment

Congratulations! You successfully deployed the WireGuard gateway charm.

You can clean up your environment by following this guide:
{ref}`Tear down your test environment <juju:tear-things-down>`

## Next steps

You achieved a basic deployment of the WordPress charm. If you want to go farther in your deployment
or learn more about the charm, check out these pages:

- Perform basic operations with your deployment like
  [installing plugins](how_to_install_plugins)
  or [themes](how_to_install_themes).
- Set up monitoring for your deployment by
  [integrating with the Canonical Observability Stack (COS)](how_to_integrate_with_cos).
- Make your deployment more secure by [enabling antispam](how_to_enable_antispam) or
  [rotating secrets](how_to_rotate_secrets),
  and learn more about the charm's security in
  [Security overview](explanation_security_overview).
- Learn more about the available [relation endpoints](reference_relation_endpoints)
  for the WordPress charm.
