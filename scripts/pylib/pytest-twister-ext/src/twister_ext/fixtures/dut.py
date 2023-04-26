import logging
from typing import Generator, Type

import pytest

from twister_ext.device.device_abstract import DeviceAbstract
from twister_ext.device.factory import DeviceFactory
from twister_ext.twister_ext_config import TwisterExtConfig, DeviceConfig

logger = logging.getLogger(__name__)


@pytest.fixture(scope='function')
def dut(request: pytest.FixtureRequest) -> Generator[DeviceAbstract, None, None]:
    """Return device instance."""
    twister_ext_config: TwisterExtConfig = request.config.twister_ext_config  # type: ignore
    device_config: DeviceConfig = twister_ext_config.devices[0]
    device_type = device_config.type

    device_class: Type[DeviceAbstract] = DeviceFactory.get_device(device_type)

    device = device_class(device_config)

    try:
        device.connect()
        device.generate_command()
        device.initialize_log_files()
        device.flash_and_run()
        device.connect()
        yield device
    except KeyboardInterrupt:
        pass
    finally:  # to make sure we close all running processes after user broke execution
        device.disconnect()
        device.stop()
