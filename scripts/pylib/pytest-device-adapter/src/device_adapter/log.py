from __future__ import annotations

import logging.config
import os

import pytest


def configure_logging(config: pytest.Config) -> None:
    """Configure logging."""
    output_dir = config.option.output_dir
    os.makedirs(output_dir, exist_ok=True)
    log_file = os.path.join(output_dir, 'device_adapter.log')

    if hasattr(config, 'workerinput'):
        worker_id = config.workerinput['workerid']
        log_file = os.path.join(output_dir, f'device_adapter_{worker_id}.log')

    log_format = '%(asctime)s:%(levelname)s:%(name)s: %(message)s'
    log_level = config.getoption('--log-level') or config.getini('log_level') or logging.INFO
    log_file = config.getoption('--log-file') or config.getini('log_file') or log_file
    log_format = config.getini('log_cli_format') or log_format

    default_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': log_format,
            },
            'simply': {
                'format': '%(message)s'
            }
        },
        'handlers': {
            'file': {
                'class': 'logging.FileHandler',
                'level': 'DEBUG',
                'formatter': 'standard',
                'filters': [],
                'filename': log_file,
                'encoding': 'utf8',
                'mode': 'w'
            },
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'DEBUG',
                'formatter': 'standard',
                'filters': [],
            }
        },
        'loggers': {
            '': {
                'handlers': ['console', 'file'],
                'level': 'WARNING',
                'propagate': False
            },
            'device_adapter': {
                'handlers': ['console', 'file'],
                'level': log_level,
                'propagate': False,
            }
        }
    }

    logging.config.dictConfig(default_config)
