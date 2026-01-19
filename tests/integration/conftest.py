# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for charm integration tests."""

import pathlib
import subprocess
import typing
from collections.abc import Generator

import jubilant
import pytest


@pytest.fixture(name="wireguard_gateway_charm_file", scope="session")
def wireguard_gateway_charm_file_fixture(pytestconfig: pytest.Config):
    """Build or get the wireguard-gateway charm file."""
    charm = pytestconfig.getoption("--charm-file")
    if charm:
        return charm

    try:
        subprocess.run(
            ["charmcraft", "pack", "--bases-index=0"], check=True, capture_output=True, text=True
        )  # nosec B603, B607
    except subprocess.CalledProcessError as exc:
        raise OSError(f"Error packing charm: {exc}; Stderr:\n{exc.stderr}") from None

    charm_path = pathlib.Path(__file__).parent.parent.parent
    charms = [p.absolute() for p in charm_path.glob("wireguard-gateway_*.charm")]
    assert charms, "wireguard-gateway .charm file not found"
    return str(charms[0])


@pytest.fixture(scope="session", name="juju")
def juju_fixture(request: pytest.FixtureRequest) -> Generator[jubilant.Juju, None, None]:
    """Pytest fixture that wraps :meth:`jubilant.with_model`."""

    def show_debug_log(juju: jubilant.Juju):
        """Show debug log.

        Args:
            juju: the Juju object.
        """
        if request.session.testsfailed:
            log = juju.debug_log(limit=1000)
            print(log, end="")

    use_existing = request.config.getoption("--use-existing", default=False)
    if use_existing:
        juju = jubilant.Juju()
        yield juju
        show_debug_log(juju)
        return

    model = request.config.getoption("--model")
    if model:
        juju = jubilant.Juju(model=model)
        yield juju
        show_debug_log(juju)
        return

    keep_models = typing.cast(bool, request.config.getoption("--keep-models"))
    with jubilant.temp_model(keep=keep_models) as juju:
        juju.wait_timeout = 10 * 60
        yield juju
        show_debug_log(juju)
        return
