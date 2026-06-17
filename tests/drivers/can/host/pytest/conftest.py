# Copyright (c) 2024 Vestas Wind Systems A/S
#
# SPDX-License-Identifier: Apache-2.0

"""
Configuration of Zephyr CAN <=> host CAN test suite.
"""

import logging
import re

import pytest
from can import Bus, BusABC
from can_shell import CanShellBus
from twister_harness import DeviceAdapter, Shell

logger = logging.getLogger(__name__)

# #region agent log
import json as _json
import subprocess as _subprocess
import time as _time

_DBG_LOG_PATH = '/home/maciej/Projects/zephyrproject/zephyr/.cursor/debug-487cff.log'


def _dbg(hyp: str, message: str, data: dict) -> None:
    """Emit a debug record to the CI pytest log and (locally) to the NDJSON file."""
    logger.warning('AGENTDBG [%s] %s :: %s', hyp, message, data)
    try:
        with open(_DBG_LOG_PATH, 'a', encoding='utf-8') as _f:
            _f.write(
                _json.dumps(
                    {
                        'sessionId': '487cff',
                        'runId': 'run1',
                        'hypothesisId': hyp,
                        'location': 'conftest.py',
                        'message': message,
                        'data': data,
                        'timestamp': int(_time.time() * 1000),
                    }
                )
                + '\n'
            )
    except OSError:
        pass


def _dump_host_iface(channel: str) -> None:
    """Dump host CAN interface admin state, bitrate, and error counters."""
    try:
        out = _subprocess.run(
            ['ip', '-details', '-statistics', 'link', 'show', channel],
            capture_output=True,
            text=True,
            timeout=5,
        )
        _dbg(
            'H2H3',
            f'host iface "{channel}" ip link',
            {'rc': out.returncode, 'stdout': out.stdout, 'stderr': out.stderr},
        )
    except Exception as exc:  # noqa: BLE001
        _dbg('H2H3', f'host iface "{channel}" ip link FAILED', {'error': repr(exc)})
# #endregion


def pytest_addoption(parser) -> None:
    """Add local parser options to pytest."""
    parser.addoption(
        '--can-context',
        default=None,
        help='Configuration context to use for python-can (default: None)',
    )


@pytest.fixture(name='context', scope='session')
def fixture_context(request, dut: DeviceAdapter) -> str:
    """Return the name of the python-can configuration context to use."""
    ctx = request.config.getoption('--can-context')

    if ctx is None:
        for fixture in dut.device_config.fixtures:
            if fixture.startswith('can:'):
                ctx = fixture.split(sep=':', maxsplit=1)[1]
                break

    logger.info('using python-can configuration context "%s"', ctx)
    return ctx


@pytest.fixture(name='chosen', scope='module')
def fixture_chosen(shell: Shell) -> str:
    """Return the name of the zephyr,canbus devicetree chosen device."""
    chosen_regex = re.compile(r'zephyr,canbus:\s+(\S+)')
    lines = shell.get_filtered_output(shell.exec_command('can_host chosen'))

    for line in lines:
        m = chosen_regex.match(line)
        if m:
            chosen = m.groups()[0]
            logger.info('testing on zephyr,canbus chosen device "%s"', chosen)
            return chosen

    pytest.fail('zephyr,canbus chosen device not found or not ready')
    return None


@pytest.fixture
def can_dut(dut: DeviceAdapter, shell: Shell, chosen: str) -> BusABC:
    """Return DUT CAN bus."""
    bus = CanShellBus(dut, shell, chosen)
    yield bus
    bus.shutdown()
    dut.clear_buffer()


@pytest.fixture
def can_host(context: str) -> BusABC:
    """Return host CAN bus."""
    bus = Bus(config_context=context)

    # #region agent log
    _channel = str(getattr(bus, 'channel', None) or context or 'can0')
    _dbg(
        'H1H2H3',
        'host bus created',
        {
            'channel': _channel,
            'state': str(getattr(bus, 'state', None)),
            'protocol': str(getattr(bus, 'protocol', None)),
            'channel_info': str(getattr(bus, 'channel_info', None)),
        },
    )
    _dump_host_iface(_channel)
    # #endregion

    yield bus

    # #region agent log
    _dump_host_iface(_channel)
    # #endregion

    bus.shutdown()
