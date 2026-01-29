# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

import ipaddress
import textwrap
import unittest.mock

import keepalived


def test_keepalived_config(monkeypatch):
    """
    arrange: define vips and check routes.
    act: call keepalived._keepalived_render_config.
    assert: verify generated configuration against expected string.
    """
    vips = [ipaddress.ip_interface("192.168.1.100/24")]
    check_routes = [ipaddress.ip_network("10.0.0.0/24")]

    config = keepalived._keepalived_render_config(vips, check_routes)

    expected_config = textwrap.dedent(
        """\
        global_defs {
          router_id 172.16.0.0
        }

        vrrp_script check_route_0 {
          script "/check_route 10.0.0.0/24"
          interval 2
          timeout 1
          fall 1
          rise 1
        }

        vrrp_instance vrrp_0 {
          state BACKUP
          interface eth0
          virtual_router_id 1
          priority 127
          advert_int 1

          virtual_ipaddress {
            192.168.1.100/24 dev eth0
          }
        }

        vrrp_sync_group vrrp_group {
          group {
            vrrp_0
          }

          track_script {
            check_route_0 weight -1
          }
        }"""
    )
    assert config == expected_config


def test_keepalived_reload_changed(monkeypatch, tmp_path):
    """
    arrange: create old config file and mock systemd (running).
    act: call keepalived.keepalived_reload.
    assert: verify config file updated and service reloaded.
    """
    conf_file = tmp_path / "keepalived.conf"
    conf_file.write_text("old config", encoding="utf-8")
    monkeypatch.setattr(keepalived, "_KEEPALIVED_CONF_FILE", conf_file)

    mock_service_reload = unittest.mock.MagicMock()
    mock_service_start = unittest.mock.MagicMock()
    monkeypatch.setattr(keepalived.systemd, "service_reload", mock_service_reload)
    monkeypatch.setattr(keepalived.systemd, "service_start", mock_service_start)
    monkeypatch.setattr(keepalived.systemd, "service_running", lambda s: True)

    vips = [ipaddress.ip_interface("192.168.1.100/24")]
    check_routes: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []

    keepalived.keepalived_reload(vips, check_routes)

    assert conf_file.read_text(encoding="utf-8") != "old config"
    mock_service_reload.assert_called_once_with("keepalived")
    mock_service_start.assert_not_called()


def test_keepalived_reload_not_running(monkeypatch, tmp_path):
    """
    arrange: mock systemd (not running).
    act: call keepalived.keepalived_reload.
    assert: verify service started instead of reloaded.
    """
    conf_file = tmp_path / "keepalived.conf"

    monkeypatch.setattr(keepalived, "_KEEPALIVED_CONF_FILE", conf_file)

    mock_service_reload = unittest.mock.MagicMock()
    mock_service_start = unittest.mock.MagicMock()
    monkeypatch.setattr(keepalived.systemd, "service_reload", mock_service_reload)
    monkeypatch.setattr(keepalived.systemd, "service_start", mock_service_start)
    monkeypatch.setattr(keepalived.systemd, "service_running", lambda s: False)

    vips = [ipaddress.ip_interface("192.168.1.100/24")]
    check_routes: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []

    keepalived.keepalived_reload(vips, check_routes)

    mock_service_start.assert_called_once_with("keepalived")
    mock_service_reload.assert_not_called()
