# WireGuard gateway operator

A [Juju](https://juju.is/) [charm](https://documentation.ubuntu.com/juju/3.6/reference/charm/) deploying a highly available, high-performance site-to-site VPN based on WireGuard.

Like any Juju charm, this charm supports one-line deployment, configuration, integration, scaling, and more. For the Charmed WireGuard gateway, this includes:

* automatic WireGuard key exchange and interface management
* automatic route management and fault tolerance using OSPF on BIRD
* virtual redundant routing using VRRP on keepalived

This charm will make operating highly available, high-performance site-to-site VPN simple and straightforward for DevOps or SRE teams through Juju's clean interface. 

## In this documentation

|                                                                                                               |                                                                                              |
|---------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------|
| [Tutorials](./tutorial.md)</br>  Get started - a hands-on introduction to using the charm for new users </br> | [How-to guides](./how-to) </br> Step-by-step guides covering key operations and common tasks |
| [Reference](./reference) </br> Technical information - specifications, APIs, architecture                     | [Explanation](./explanation) </br> Concepts - discussion and clarification of key topics     |

## Contributing to this documentation

Documentation is an important part of this project, and we take the same open-source approach
to the documentation as the code. As such, we welcome community contributions, suggestions, and
constructive feedback on our documentation.
See [How to contribute](./how-to/contribute.md) for more information.


If there's a particular area of documentation that you'd like to see that's missing, please 
[file a bug](https://github.com/canonical/wireguard-gateway-operator/issues).

## Project and community

The WireGuard gateway operator is a member of the Ubuntu family. 
It's an open source project that warmly welcomes community projects, contributions, suggestions, fixes and constructive feedback.

- [Code of conduct](https://ubuntu.com/community/code-of-conduct)
- [Get support](https://discourse.charmhub.io/)
- [Contribute](CONTRIBUTING.md)
- [Matrix](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)

Thinking about using the WireGuard gateway operator for your next project? 
[Get in touch](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)!

# Contents

1. [Tutorial](./tutorial.md)
1. [How-to](./how-to)
1. [Reference](./reference)
1. [Explanation](./explanation)
