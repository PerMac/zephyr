import logging
from typing import Generator, Type

import pytest

from device_adapter.device.device_abstract import DeviceAbstract
from device_adapter.device.factory import DeviceFactory
from device_adapter.device_adapter_config import DeviceAdapterConfig, DeviceConfig

logger = logging.getLogger(__name__)


@pytest.fixture(scope='function')
def dut(request: pytest.FixtureRequest) -> Generator[DeviceAbstract, None, None]:
    """Return device instance."""
    device_adapter_config: DeviceAdapterConfig = request.config.device_adapter_config  # type: ignore
    device_config: DeviceConfig = device_adapter_config.devices[0]
    device_type = device_config.type

    device_class: Type[DeviceAbstract] = DeviceFactory.get_device(device_type)

    device = device_class(device_config)

    try:
        device.connect()
        device.generate_command()
        device.flash_and_run()
        device.connect()
        yield device
    except KeyboardInterrupt:
        pass
    finally:  # to make sure we close all running processes after user broke execution
        device.disconnect()
        device.stop()
