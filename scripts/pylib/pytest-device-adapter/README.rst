==============
Device adapter
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

Built shell application by west and call pytest directly:

.. code-block:: sh

  cd samples/subsys/shell/shell_module
  west build -p -b nrf52840dk_nrf52840
  pytest --device-adapter --device-type=hardware --device-serial=/dev/ttyACM0 --build-dir=build

Or run this test by Twister:

.. code-block:: sh

  ./scripts/twister -vv -p nrf52840dk_nrf52840 --device-testing --device-serial /dev/ttyACM0 -T samples/subsys/shell/shell_module -s samples/subsys/shell/shell_module/sample.shell.shell_module
