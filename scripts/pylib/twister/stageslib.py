import logging
import subprocess
import sys

logger = logging.getLogger('twister')
logger.setLevel(logging.DEBUG)


class ExecutionStage:
    """
    Abstract class for test execution stages. Each inhering stage requires
    run method to be implemented
    """
    description = None

    def __init__(self, description=None, proj_builder=None):
        self.description = description
        if proj_builder:
            self.pb = proj_builder

    def run(self):
        """Define procedure to be executed at a given stage.

        Must be implemented in sub classes. Defines actions taken during a given
        stage
        """
        raise NotImplementedError(f"{self.__class__.__name__}.run()")


class CallScriptsStage(ExecutionStage):
    """ TODO: ADD description"""

    def __init__(self, description=None, proj_builder=None):
        ExecutionStage.__init__(self, description)

    def run(self):
        for script in self.description:
            s = script.split()
            run_custom_script(script=s, timeout=15)


class WestSignStage(ExecutionStage):
    """ TODO: ADD description"""
    def __init__(self, description=None, proj_builder=None):
        ExecutionStage.__init__(self, description, proj_builder)

    def run(self):
        image = self.description.get('image', 'main')
        key = self.description.get('key', 'default')
        if image == 'main':
            img_path = self.pb.instance.build_dir
        elif self.pb.instance.multi_build:
            img_path = self.pb.instance.multi_build[image]['build_dir']
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


class OnTargetStage(ExecutionStage):
    """ TODO: ADD description"""
    def __init__(self, description=None, proj_builder=None):
        ExecutionStage.__init__(self, description, proj_builder)

    def run(self):
        instance = self.pb.instance
        suite = self.pb.suite
        image = self.description.get('image', 'main')
        #instance.build_dir = instance.multi_build[image]['build_dir']
        # instance.testcase attributes have to be updated with stage specific data
        for k, v in self.description.items():
            if k in ["harness", "harness_config"]:
                setattr(instance.testcase, k, v)
        if instance.handler:
            if instance.handler.type_str == "device":
                instance.handler.suite = suite
            instance.handler.build_dir = instance.multi_build[image]['build_dir']
            # We have to update handler.instance to align with image/harness selection
            #instance.handler.instance = instance
            instance.handler.handle()

        sys.stdout.flush()


class StageContainer:
    def __init__(self, proj_builder):
        self.pb = proj_builder
        self.stages = self.get_stages()

    def __iter__(self):
        for stage in self.stages:
            yield stage

    def get_stages(self):
        stages = []
        for stage in self.pb.instance.testcase.stages:
            (name, description), = stage.items()
            # This will create a stage object of a type given in the name
            # e.g. for name=CallScript CallScriptStage(description) object
            # will be created
            ev = f"{name}Stage(description, self.pb)"
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
