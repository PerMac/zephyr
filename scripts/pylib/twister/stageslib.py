import logging
import subprocess
import sys
import os

logger = logging.getLogger('twister')
logger.setLevel(logging.DEBUG)

# TODO: Probably the time of execution of the multistaging is incorrect
# TODO: refactor and make abstract steps from DeviceHandler (monitor uart and so on)
# TODO: Lock the device until all stages done
# TODO: verify if not to much building is going on

class ExecutionStage:
    """
    Abstract class for test execution stages. Each inhering stage requires
    run method to be implemented
    """
    description = None
    zephyr_base = os.getenv("ZEPHYR_BASE")

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
            logger.debug(f"Calling: {script}")
            s = script.split()
            run_custom_script(script=s, timeout=15)



class WestSignStage(ExecutionStage):
    """ TODO: ADD description"""
    def __init__(self, description=None, proj_builder=None):
        ExecutionStage.__init__(self, description, proj_builder)

    def run(self):
        image = self.description.get('image', 'main')
        # TODO: add default key. The same with other args
        imgtool_path = os.path.join(self.zephyr_base, "../bootloader/mcuboot/scripts/imgtool.py")
        imgtool_args = {
            'key': self.description.get('key', 'default'),
            'header-size': self.description.get('header_size', '0x200'),
            'align': self.description.get('align', '8'),
            'version': self.description.get('version', '1.2'),
            'slot-size': self.description.get('slot_size', '0x67000'),
            'pad': self.description.get('pad', False),
            'hex-addr': self.description.get('hex_addr', None)
        }

        if imgtool_args['key'] == 'default':
            imgtool_args['key'] = os.path.join(self.zephyr_base,
                                               "../bootloader/mcuboot/root-rsa-2048.pem")
        else:
            imgtool_args['key'] = os.path.join(self.zephyr_base,
                                               imgtool_args['key'])

        if image == 'main':
            img_path = self.pb.instance.build_dir
        elif self.pb.instance.multi_build:
            img_path = self.pb.instance.multi_build[image]['build_dir']
        else:
            # TODO: add error?
            pass

        command = ["west", "sign", "-d", img_path, "--shex", f"{img_path}/zephyr/zephyr.hex", "-t",
                   "imgtool", "-p",
                   imgtool_path, "--"
                   ]
        for k, v in imgtool_args.items():
            if v is None:
                continue
            elif v is True:
                command.extend([f"--{k}"])
            elif v is False:
                continue
            else:
                command.extend([f"--{k}", f"{v}"])
        #command.append("--")

        print(" ".join(command))
        # TODO: Add error handling to fail the test if stage/script in stage failed
        run_custom_script(command, timeout=15)

class OnTargetStage(ExecutionStage):
    """ TODO: ADD description"""
    # TODO: -- runners.nrfjprog: mass erase requested <- solve this
    def __init__(self, description=None, proj_builder=None):
        ExecutionStage.__init__(self, description, proj_builder)

    def run(self):
        instance = self.pb.instance
        suite = self.pb.suite
        image = self.description.get('image', None)
        command = self.description.get('command', None)

        # instance.testcase attributes have to be updated with stage specific data
        for k, v in self.description.items():
            if k in ["harness", "harness_config"]:
                setattr(instance.testcase, k, v)
        if instance.handler:
            if instance.handler.type_str == "device":
                instance.handler.suite = suite
            if image:
                instance.handler.build_dir = instance.multi_build[image]['build_dir']
            # We have to update handler.instance to align with image/harness selection
            #instance.handler.instance = instance
            instance.handler.handle(command=command)

        sys.stdout.flush()


class OnTargetCommandStage(ExecutionStage):
    """ TODO: ADD description"""
    # TODO: -- runners.nrfjprog: mass erase requested <- solve this
    def __init__(self, description=None, proj_builder=None):
        ExecutionStage.__init__(self, description, proj_builder)

    def run(self):
        instance = self.pb.instance
        suite = self.pb.suite
        image = self.description.get('image', 'main')
        command = self.description.get('command', None)

        # instance.testcase attributes have to be updated with stage specific data
        for k, v in self.description.items():
            if k in ["harness", "harness_config"]:
                setattr(instance.testcase, k, v)
        if instance.handler:
            if instance.handler.type_str == "device":
                instance.handler.suite = suite


            #instance.handler.build_dir = instance.multi_build[image]['build_dir']
            # We have to update handler.instance to align with image/harness selection
            #instance.handler.instance = instance
            instance.handler.handle(command=command)

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
    # TODP: If error report test error and break test
    with subprocess.Popen(script, stderr=subprocess.PIPE,
                          stdout=subprocess.PIPE) as proc:
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            logger.debug(stdout.decode())
            if stderr:
                logger.error(stderr.decode())

        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            logger.error("{} timed out".format(script))