# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

import wireguard
import wgdb
import importlib
import ipaddress
import unittest.mock
import textwrap

def test_wg_config():
    interface = wgdb.WireguardLink(
        owner=1,
        status=wgdb.WireguardLinkStatus.OPEN,
        public_key="public_key",
        private_key="private_key",
        port=51820,
        peer_public_key="peer_public_key",
        peer_endpoint="1.2.3.4:51820",
        peer_allowed_ips=[ipaddress.ip_network("10.0.0.0/24")],
    )

    config_str_provider = wireguard._wg_config(interface, is_provider=True, quick=True)
    expected_provider = textwrap.dedent("""\
        [Interface]
        ListenPort = 51820
        PrivateKey = private_key
        Address = 169.254.0.1/24, fe80::1/64
        Table = off
    
        [Peer]
        PublicKey = peer_public_key
        AllowedIPs = 224.0.0.0/24, ff02::/16, 169.254.0.0/24, fe80::0/64,10.0.0.0/24
        Endpoint = 1.2.3.4:51820
        PersistentKeepalive = 5
    
        """).strip()
    assert config_str_provider.strip() == expected_provider

    config_str_requirer = wireguard._wg_config(interface, is_provider=False, quick=True)
    expected_requirer = textwrap.dedent("""\
        [Interface]
        ListenPort = 51820
        PrivateKey = private_key
        Address = 169.254.0.2/24, fe80::2/64
        Table = off
    
        [Peer]
        PublicKey = peer_public_key
        AllowedIPs = 224.0.0.0/24, ff02::/16, 169.254.0.0/24, fe80::0/64,10.0.0.0/24
        Endpoint = 1.2.3.4:51820
        PersistentKeepalive = 5
    
        """).strip()
    assert config_str_requirer.strip() == expected_requirer

def test_wireguard_add(monkeypatch, tmp_path):
    importlib.reload(wireguard)
    interface = wgdb.WireguardLink(
        owner=1,
        status=wgdb.WireguardLinkStatus.OPEN,
        public_key="public_key",
        private_key="private_key",
        port=51820,
        peer_public_key="peer_public_key",
        peer_endpoint="1.2.3.4:51820",
        peer_allowed_ips=[ipaddress.ip_network("10.0.0.0/24")],
    )

    monkeypatch.setattr(wireguard, "_WG_QUICK_CONFIG_DIR", tmp_path)

    mock_service_enable = unittest.mock.MagicMock()
    mock_service_start = unittest.mock.MagicMock()
    monkeypatch.setattr(wireguard.systemd, "service_enable", mock_service_enable)
    monkeypatch.setattr(wireguard.systemd, "service_start", mock_service_start)
    monkeypatch.setattr(wireguard.systemd, "service_running", lambda s: True)

    wireguard.wireguard_add(interface, is_provider=True)

    conf_file = tmp_path / f"{interface.interface_name}.conf"
    assert conf_file.exists()
    mock_service_enable.assert_called_once_with(f"wg-quick@{interface.interface_name}")
    mock_service_start.assert_called_once_with(f"wg-quick@{interface.interface_name}")

def test_wireguard_remove(monkeypatch, tmp_path):
    importlib.reload(wireguard)
    interface = wgdb.WireguardLink(
        owner=1,
        status=wgdb.WireguardLinkStatus.OPEN,
        public_key="public_key",
        private_key="private_key",
        port=51820,
        peer_public_key="peer_public_key",
        peer_endpoint="1.2.3.4:51820",
        peer_allowed_ips=[ipaddress.ip_network("10.0.0.0/24")],
    )

    monkeypatch.setattr(wireguard, "_WG_QUICK_CONFIG_DIR", tmp_path)
    conf_file = tmp_path / f"{interface.interface_name}.conf"
    conf_file.touch()

    mock_service_stop = unittest.mock.MagicMock()
    mock_service_disable = unittest.mock.MagicMock()
    monkeypatch.setattr(wireguard.systemd, "service_stop", mock_service_stop)
    monkeypatch.setattr(wireguard.systemd, "service_disable", mock_service_disable)

    wireguard.wireguard_remove(interface)

    assert not conf_file.exists()
    mock_service_stop.assert_called_once_with(f"wg-quick@{interface.interface_name}")
    mock_service_disable.assert_called_once_with(f"wg-quick@{interface.interface_name}")

def test_wireguard_syncconf(monkeypatch, tmp_path):
    importlib.reload(wireguard)
    interface = wgdb.WireguardLink(
        owner=1,
        status=wgdb.WireguardLinkStatus.OPEN,
        public_key="public_key",
        private_key="private_key",
        port=51820,
        peer_public_key="peer_public_key",
        peer_endpoint="1.2.3.4:51820",
        peer_allowed_ips=[ipaddress.ip_network("10.0.0.0/24")],
    )

    monkeypatch.setattr(wireguard, "_WG_QUICK_CONFIG_DIR", tmp_path)

    mock_check_output = unittest.mock.MagicMock(return_value="")
    monkeypatch.setattr(wireguard.subprocess, "check_output", mock_check_output)

    wireguard.wireguard_syncconf(interface, is_provider=True)

    mock_check_output.assert_called_once_with(
        ["wg", "syncconf", interface.interface_name, "/dev/stdin"],
        input=unittest.mock.ANY,
    )
    conf_file = tmp_path / f"{interface.interface_name}.conf"
    assert conf_file.exists()
