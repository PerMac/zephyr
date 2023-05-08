==============
Twister ext
==============

Installation
------------

Installation from the source:

.. code-block:: sh

  pip install .


Installation the project in editable mode:

.. code-block:: sh

  pip install -e .


Usage
-----

Build shell application by west and call pytest directly:

.. code-block:: sh

  cd ${ZEPHYR_BASE}/samples/subsys/testsuite/pytest/shell

  # native_posix
  west build -p -b native_posix -- -DCONFIG_NATIVE_UART_0_ON_STDINOUT=y
  pytest --twister-ext --device-type=native --build-dir=build

  # QEMU
  west build -p -b qemu_x86 -- -DQEMU_PIPE=qemu-fifo
  pytest --twister-ext --device-type=qemu --build-dir=build

  # hardware
  west build -p -b nrf52840dk_nrf52840
  pytest --twister-ext --device-type=hardware --device-serial=/dev/ttyACM0 --build-dir=build

Or run this test by Twister:

.. code-block:: sh

  cd ${ZEPHYR_BASE}

  # native_posix & QEMU
  ./scripts/twister -p native_posix -p qemu_x86 -T samples/subsys/testsuite/pytest/shell

  # hardware
  ./scripts/twister -p nrf52840dk_nrf52840 --device-testing --device-serial /dev/ttyACM0 -T samples/subsys/testsuite/pytest/shell
