from __future__ import annotations

import abc
import logging
import os
from typing import Generator

from twister_ext.log_files.log_file import LogFile, NullLogFile
from twister_ext.twister_ext_config import DeviceConfig

logger = logging.getLogger(__name__)


class DeviceAbstract(abc.ABC):
    """Class defines an interface for all devices."""

    def __init__(self, device_config: DeviceConfig, **kwargs) -> None:
        """
        :param device_config: device configuration
        """
        self.device_config: DeviceConfig = device_config
        self.handler_log_file: LogFile = NullLogFile.create()
        self.device_log_file: LogFile = NullLogFile.create()

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}()'

    @property
    def env(self) -> dict[str, str]:
        env = os.environ.copy()
        return env

    @abc.abstractmethod
    def connect(self, timeout: float = 1) -> None:
        """Connect with the device (e.g. via UART)"""

    @abc.abstractmethod
    def disconnect(self) -> None:
        """Close a connection with the device"""

    @abc.abstractmethod
    def generate_command(self) -> None:
        """
        Generate command which will be used during flashing or running device.
        """

    def flash_and_run(self) -> None:
        """
        Flash and run application on a device.

        :param timeout: time out in seconds
        """

    @property
    @abc.abstractmethod
    def iter_stdout(self) -> Generator[str, None, None]:
        """Iterate stdout from a device."""

    @abc.abstractmethod
    def send(self, data: bytes) -> None:
        """Send data to device"""

    @abc.abstractmethod
    def initialize_log_files(self):
        """
        Initialize file to store logs.
        """

    def stop(self) -> None:
        """Stop device."""
