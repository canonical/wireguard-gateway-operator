(explanation_security)=

# Security overview

The WireGuard gateway charm uses WireGuard as the VPN protocol for site-to-site traffic. WireGuard is a modern VPN solution that uses state-of-the-art cryptography reviewed by cryptographers. It has been designed with ease of implementation and simplicity in mind to minimize the attack surface.

You can learn more about the security of the WireGuard protocol from the [WireGuard technical paper](https://www.wireguard.com/papers/wireguard.pdf)
and [Formal Verification of the WireGuard protocol](https://www.wireguard.com/formal-verification/).

WireGuard gateway charm leverages the asymmetric cryptographic properties of the WireGuard protocol to ensure that only public keys are exchanged between charms, and private keys never leave the machine.
