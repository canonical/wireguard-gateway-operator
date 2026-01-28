# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

import ipaddress
import importlib
import unittest.mock
import textwrap
import bird
import wgdb


def test_bird_config():
    interfaces = [
        wgdb.WireguardLink(
            owner=1,
            status=wgdb.WireguardLinkStatus.OPEN,
            public_key="public_key",
            private_key="private_key",
            port=51820,
            peer_public_key="peer_public_key",
            peer_endpoint="1.2.3.4:51820",
            peer_allowed_ips=[ipaddress.ip_network("10.0.0.0/24")],
        )
    ]
    advertise_prefixes = [ipaddress.ip_network("192.168.1.0/24")]

    config = bird.bird_config("1.1.1.1", interfaces, advertise_prefixes)

    expected = textwrap.dedent("""\
        router id 1.1.1.1;

        protocol kernel k4 {
          ipv4 { import none; export all; };
          merge paths yes limit 64;
        }

        protocol kernel k6 {
          ipv6 { import none; export all; };
          merge paths yes limit 64;
        }

        protocol device {}

        protocol ospf v3 OSPF6 {
          rfc5838 yes;
          ecmp yes limit 64;
          instance id 0;
          ipv6 { import all; export none; };

          area 0.0.0.0 {
            interface "wg51820" { type ptp; cost 10; hello 5; dead 30; };
          };
        }

        protocol ospf v3 OSPF4 {
          rfc5838 yes;
          ecmp yes limit 64;
          instance id 64;
          ipv4 { import all; export none; };

          area 0.0.0.0 {
            interface "wg51820" { type ptp; cost 10; hello 5; dead 30; };
            stubnet 169.254.0.0/24 { hidden; };
            stubnet 192.168.1.0/24 { cost 10; };
          };
        }""")
    assert config == expected


def test_bird_reload_changed(monkeypatch, tmp_path):
    importlib.reload(bird)
    conf_file = tmp_path / "bird.conf"
    conf_file.write_text("old config", encoding="utf-8")
    monkeypatch.setattr(bird, "_BIRD_CONF_FILE", conf_file)

    mock_check_call = unittest.mock.MagicMock()
    monkeypatch.setattr(bird.subprocess, "check_call", mock_check_call)

    bird.bird_reload("new config")

    assert conf_file.read_text(encoding="utf-8") == "new config"
    mock_check_call.assert_called_once_with(["birdc", "configure"])


def test_bird_reload_no_change(monkeypatch, tmp_path):
    importlib.reload(bird)
    conf_file = tmp_path / "bird.conf"
    conf_file.write_text("same config", encoding="utf-8")
    monkeypatch.setattr(bird, "_BIRD_CONF_FILE", conf_file)

    mock_check_call = unittest.mock.MagicMock()
    monkeypatch.setattr(bird.subprocess, "check_call", mock_check_call)

    bird.bird_reload("same config")

    assert conf_file.read_text(encoding="utf-8") == "same config"
    mock_check_call.assert_not_called()
