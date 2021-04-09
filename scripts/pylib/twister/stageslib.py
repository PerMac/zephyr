import logging
import subprocess

logger = logging.getLogger('twister')
logger.setLevel(logging.DEBUG)


class ExecutionStage:
    """
    Abstract class for test execution stages. Each inhering stage requires
    run method to be implemented
    """
    description = None

    def __init__(self, description=None, instance=None):
        self.description = description
        if instance:
            self.instance = instance

    def run(self):
        """Define procedure to be executed at a given stage.

        Must be implemented in sub classes. Defines actions taken during a given
        stage
        """
        raise NotImplementedError(f"{self.__class__.__name__}.run()")


class CallScriptsStage(ExecutionStage):
    """ TODO: ADD description"""

    def __init__(self, description=None, instance=None):
        ExecutionStage.__init__(self, description)

    def run(self):
        for script in self.description:
            s = script.split()
            run_custom_script(script=s, timeout=15)


class WestSignStage(ExecutionStage):
    """ TODO: ADD description"""
    def __init__(self, description=None, instance=None):
        ExecutionStage.__init__(self, description, instance)

    def run(self):
        image = self.description.get('image', 'main')
        key = self.description.get('key', 'default')
        if image == 'main':
            img_path = self.instance.build_dir
        elif self.instance.multi_build:
            img_path = self.instance.multi_build[image]['build_dir']
        else:
            # TODO: add error?
            pass

        if key == 'default':
            # TODO: add default key
            pass

        command = ["west", "sign", "-d", img_path, "-H", "zephyr.hex", "-t",
                   "imgtool", "-p",
                   "/home/maciej/zephyrproject2/bootloader/mcuboot/scripts/imgtool.py",
                   "--", "--key", key]
        run_custom_script(command, timeout=15)


def get_stages(instance):
    stages = []
    for stage in instance.testcase.stages:
        (name, description), = stage.items()
        # This will create a stage object of a type given in the name
        # e.g. for CallScript name CallScriptStage(description) object
        # will be created
        ev = f"{name}Stage(description, instance)"
        stages.append(eval(ev))

    return stages


def run_custom_script(script, timeout):
    with subprocess.Popen(script, stderr=subprocess.PIPE,
                          stdout=subprocess.PIPE) as proc:
        try:
            stdout, _ = proc.communicate(timeout=timeout)
            logger.debug(stdout.decode())

        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            logger.error("{} timed out".format(script))
