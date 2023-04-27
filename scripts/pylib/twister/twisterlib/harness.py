# SPDX-License-Identifier: Apache-2.0
from asyncio.log import logger
import re
import os
import sys
import subprocess
import shlex
from collections import OrderedDict
import xml.etree.ElementTree as ET
import logging

logger = logging.getLogger('twister')
logger.setLevel(logging.DEBUG)

# pylint: disable=anomalous-backslash-in-string
result_re = re.compile(".*(PASS|FAIL|SKIP) - (test_)?(.*) in (\d*[.,]?\d*) seconds")
class Harness:
    GCOV_START = "GCOV_COVERAGE_DUMP_START"
    GCOV_END = "GCOV_COVERAGE_DUMP_END"
    FAULT = "ZEPHYR FATAL ERROR"
    RUN_PASSED = "PROJECT EXECUTION SUCCESSFUL"
    RUN_FAILED = "PROJECT EXECUTION FAILED"
    run_id_pattern = r"RunID: (?P<run_id>.*)"


    ztest_to_status = {
        'PASS': 'passed',
        'SKIP': 'skipped',
        'BLOCK': 'blocked',
        'FAIL': 'failed'
        }

    def __init__(self):
        self.state = None
        self.type = None
        self.regex = []
        self.matches = OrderedDict()
        self.ordered = True
        self.repeat = 1
        self.testcases = []
        self.id = None
        self.fail_on_fault = True
        self.fault = False
        self.capture_coverage = False
        self.next_pattern = 0
        self.record = None
        self.recording = []
        self.fieldnames = []
        self.ztest = False
        self.detected_suite_names = []
        self.run_id = None
        self.matched_run_id = False
        self.run_id_exists = False
        self.instance = None
        self.testcase_output = ""
        self._match = False

    def configure(self, instance):
        self.instance = instance
        config = instance.testsuite.harness_config
        self.id = instance.testsuite.id
        self.run_id = instance.run_id
        if instance.testsuite.ignore_faults:
            self.fail_on_fault = False

        if config:
            self.type = config.get('type', None)
            self.regex = config.get('regex', [])
            self.repeat = config.get('repeat', 1)
            self.ordered = config.get('ordered', True)
            self.record = config.get('record', {})

    def process_test(self, line):

        runid_match = re.search(self.run_id_pattern, line)
        if runid_match:
            run_id = runid_match.group("run_id")
            self.run_id_exists = True
            if run_id == str(self.run_id):
                self.matched_run_id = True

        if self.RUN_PASSED in line:
            if self.fault:
                self.state = "failed"
            else:
                self.state = "passed"

        if self.RUN_FAILED in line:
            self.state = "failed"

        if self.fail_on_fault:
            if self.FAULT == line:
                self.fault = True

        if self.GCOV_START in line:
            self.capture_coverage = True
        elif self.GCOV_END in line:
            self.capture_coverage = False

class Console(Harness):

    def configure(self, instance):
        super(Console, self).configure(instance)
        if self.type == "one_line":
            self.pattern = re.compile(self.regex[0])
        elif self.type == "multi_line":
            self.patterns = []
            for r in self.regex:
                self.patterns.append(re.compile(r))

    def handle(self, line):
        if self.type == "one_line":
            if self.pattern.search(line):
                self.state = "passed"
        elif self.type == "multi_line" and self.ordered:
            if (self.next_pattern < len(self.patterns) and
                self.patterns[self.next_pattern].search(line)):
                self.next_pattern += 1
                if self.next_pattern >= len(self.patterns):
                    self.state = "passed"
        elif self.type == "multi_line" and not self.ordered:
            for i, pattern in enumerate(self.patterns):
                r = self.regex[i]
                if pattern.search(line) and not r in self.matches:
                    self.matches[r] = line
            if len(self.matches) == len(self.regex):
                self.state = "passed"
        else:
            logger.error("Unknown harness_config type")

        if self.fail_on_fault:
            if self.FAULT in line:
                self.fault = True

        if self.GCOV_START in line:
            self.capture_coverage = True
        elif self.GCOV_END in line:
            self.capture_coverage = False


        if self.record:
            pattern = re.compile(self.record.get("regex", ""))
            match = pattern.search(line)
            if match:
                csv = []
                if not self.fieldnames:
                    for k,v in match.groupdict().items():
                        self.fieldnames.append(k)

                for k,v in match.groupdict().items():
                    csv.append(v.strip())
                self.recording.append(csv)

        self.process_test(line)

        tc = self.instance.get_case_or_create(self.id)
        if self.state == "passed":
            tc.status = "passed"
        else:
            tc.status = "failed"


class PytestHarnessException(Exception):
    """General exception for pytest."""


class Pytest(Harness):

    def configure(self, instance):
        super(Pytest, self).configure(instance)
        self.running_dir = instance.build_dir
        self.source_dir = instance.testsuite.source_dir
        self.report_file = os.path.join(self.running_dir, 'report.xml')
        self.reserved_serial = None

    def pytest_run(self):
        try:
            cmd = self.generate_command()
            if not cmd:
                logger.error('Pytest command not generated, check logs')
                return
            self.run_command(cmd)
        except PytestHarnessException as pytest_exception:
            logger.error(str(pytest_exception))
        finally:
            if self.reserved_serial:
                self.instance.handler.make_device_available(self.reserved_serial)
        self._apply_instance_status()

    def generate_command(self):
        config = self.instance.testsuite.harness_config
        pytest_root = config.get('pytest_root', 'pytest') if config else 'pytest'
        pytest_args = config.get('pytest_args', []) if config else []
        command = [
            'pytest',
            '--twister-ext',
            '-s',
            '-q',
            os.path.join(self.source_dir, pytest_root),
            f'--build-dir={self.running_dir}',
            f'--junit-xml={self.report_file}'
        ]
        command.extend(pytest_args)

        handler = self.instance.handler
        if handler.type_str == 'device':
            command.extend(
                self._generate_parameters_for_hardware(handler)
            )
        elif any([
            handler.type_str == 'qemu',
            handler.type_str == 'native',
            handler.type_str == 'unit',
        ]):
            command.append(f'--device-type={handler.type_str}')
        elif handler.type_str == 'build':
            command.append('--device-type=custom')
        else:
            raise PytestHarnessException(f'Handling of handler {handler.type_str} not implemented yet')
        return command

    def _generate_parameters_for_hardware(self, handler):
        command = ['--device-type=hardware']
        hardware = handler.get_hardware()
        if not hardware:
            raise PytestHarnessException('Hardware is not available')

        self.reserved_serial = hardware.serial_pty or hardware.serial
        if hardware.serial_pty:
            command.append(f'--device-serial-pty={hardware.serial_pty}')
        else:
            command.extend([
                f'--device-serial={hardware.serial}',
                f'--device-serial-baud={hardware.baud}'
            ])

        options = handler.options
        if runner := hardware.runner or options.west_runner:
            command.append(f'--runner={runner}')

        if options.west_flash and options.west_flash != []:
            command.append(f'--west-flash-extra-args={options.west_flash}')

        if board_id := hardware.probe_id or hardware.id:
            command.append(f'--device-id={board_id}')

        if hardware.product:
            command.append(f'--device-product={hardware.product}')

        # TODO:
        # pre_script = hardware.pre_script
        # post_flash_script = hardware.post_flash_script
        # post_script = hardware.post_script
        return command

    def run_command(self, cmd):
        logger.debug('Running pytest command: %s', ' '.join(shlex.quote(a) for a in cmd))
        with subprocess.Popen(cmd,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT) as proc:
            try:
                proc.communicate()
                tree = ET.parse(self.report_file)
                root = tree.getroot()
                for child in root:
                    if child.tag == 'testsuite':
                        if child.attrib['failures'] != '0':
                            self.state = "failed"
                        elif child.attrib['skipped'] != '0':
                            self.state = "skipped"
                        elif child.attrib['errors'] != '0':
                            self.state = "error"
                        else:
                            self.state = "passed"
                        self.instance.execution_time = float(child.attrib['time'])
            except subprocess.TimeoutExpired:
                proc.kill()
                self.state = "failed"
            except ET.ParseError:
                self.state = "failed"
            except IOError:
                logger.warning("Can't access report.xml")
                self.state = "failed"

        tc = self.instance.get_case_or_create(self.id)
        if self.state == "passed":
            tc.status = "passed"
            logger.debug("Pytest cases passed")
        elif self.state == "skipped":
            tc.status = "skipped"
            logger.debug("Pytest cases skipped.")
        else:
            tc.status = "failed"
            logger.info("Pytest cases failed.")

    def _apply_instance_status(self):
        if self.state:
            self.instance.status = self.state
            if self.state in ["error", "failed"]:
                self.instance.reason = "Pytest failed"
        else:
            self.instance.status = "failed"
            self.instance.reason = "Pytest timeout"
        if self.instance.status in ["error", "failed"]:
            self.instance.add_missing_case_status("blocked", self.instance.reason)


class Test(Harness):
    RUN_PASSED = "PROJECT EXECUTION SUCCESSFUL"
    RUN_FAILED = "PROJECT EXECUTION FAILED"
    test_suite_start_pattern = r"Running TESTSUITE (?P<suite_name>.*)"
    ZTEST_START_PATTERN = r"START - (test_)?(.*)"

    def handle(self, line):
        test_suite_match = re.search(self.test_suite_start_pattern, line)
        if test_suite_match:
            suite_name = test_suite_match.group("suite_name")
            self.detected_suite_names.append(suite_name)

        testcase_match = re.search(self.ZTEST_START_PATTERN, line)
        if testcase_match:
            name = "{}.{}".format(self.id, testcase_match.group(2))
            tc = self.instance.get_case_or_create(name)
            # Mark the test as started, if something happens here, it is mostly
            # due to this tests, for example timeout. This should in this case
            # be marked as failed and not blocked (not run).
            tc.status = "started"

        if testcase_match or self._match:
            self.testcase_output += line + "\n"
            self._match = True

        result_match = result_re.match(line)

        if result_match and result_match.group(2):
            matched_status = result_match.group(1)
            name = "{}.{}".format(self.id, result_match.group(3))
            tc = self.instance.get_case_or_create(name)
            tc.status = self.ztest_to_status[matched_status]
            if tc.status == "skipped":
                tc.reason = "ztest skip"
            tc.duration = float(result_match.group(4))
            if tc.status == "failed":
                tc.output = self.testcase_output
            self.testcase_output = ""
            self._match = False
            self.ztest = True

        self.process_test(line)

        if not self.ztest and self.state:
            logger.debug(f"not a ztest and no state for  {self.id}")
            tc = self.instance.get_case_or_create(self.id)
            if self.state == "passed":
                tc.status = "passed"
            else:
                tc.status = "failed"


class Ztest(Test):
    pass


class HarnessImporter:

    @staticmethod
    def get_harness(harness_name):
        thismodule = sys.modules[__name__]
        if harness_name:
            harness_class = getattr(thismodule, harness_name)
        else:
            harness_class = getattr(thismodule, 'Test')
        return harness_class()
