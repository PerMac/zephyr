import time
import logging
import pytest

from twister_ext.device.device_abstract import DeviceAbstract

logger = logging.getLogger(__name__)


def wait_for_message(iter_stdout, message, timeout=60):
    time_started = time.time()
    for line in iter_stdout:
        if line:
            logger.debug("#: " + line)
        if message in line:
            return True
        if time.time() > time_started + timeout:
            return False


def test_shell_print_help(dut: DeviceAbstract):
    time.sleep(1)  # wait for application initialization on DUT

    dut.connection.write(b'help\n')
    assert wait_for_message(dut.iter_stdout, "see all available commands")


def test_shell_print_version(dut: DeviceAbstract):
    time.sleep(1)  # wait for application initialization on DUT

    dut.connection.write(b'version\n')
    assert wait_for_message(dut.iter_stdout, "Zephyr")
