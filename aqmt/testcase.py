"""
This module contains the individual test case logic
"""

from datetime import datetime
import functools
import os
from plumbum import local
from plumbum.cmd import bash
import re
import shutil
import time

from . import calc_queuedelay
from . import calc_tagged_rate
from . import calc_utilization
from . import calc_window
from . import logger
from . import processes
from .terminal import get_log_cmd
from .testenv import get_pid_ta, remove_hint, save_hint_to_folder, set_pid_ta, read_metadata


def analyze_test(testfolder, samples_to_skip):
    bitrate = 0
    with open(testfolder + '/details', 'r') as f:
        for line in f:
            if line.startswith('testbed_rate'):
                bitrate = int(line.split()[1])
                break

    if bitrate == 0:
        raise Exception("Could not determine bitrate of test '%s'" % testfolder)

    # FIXME: properly handle rtt for different queues/servers
    metadata_kv, metadata_lines = read_metadata(testfolder + '/details')
    rtt_l4s = float(metadata_kv['testbed_rtt_servera']) + float(metadata_kv['testbed_rtt_clients'])
    rtt_classic = float(metadata_kv['testbed_rtt_servera']) + float(metadata_kv['testbed_rtt_clients'])

    # the derived folder contains per sample data derived data
    # from analyzer data
    if not os.path.exists(testfolder + '/derived'):
        os.makedirs(testfolder + '/derived')

    # the aggregated folder contains aggregated numbers used in
    # collection comparison plots
    if not os.path.exists(testfolder + '/aggregated'):
        os.makedirs(testfolder + '/aggregated')

    program = os.path.join(os.path.dirname(__file__), 'calc_queue_packets_drops')
    cmd = local[program][testfolder, str(samples_to_skip)]
    logger.debug(get_log_cmd(cmd))
    cmd()

    program = os.path.join(os.path.dirname(__file__), 'calc_basic')
    cmd = local[program][testfolder, str(bitrate), str(rtt_l4s), str(rtt_classic), str(samples_to_skip)]
    logger.debug(get_log_cmd(cmd))
    cmd()

    calc_queuedelay.process_test(testfolder)
    calc_tagged_rate.process_test(testfolder, samples_to_skip)
    calc_utilization.process_test(testfolder, bitrate)
    calc_window.process_test(testfolder, rtt_l4s, rtt_classic)


class TestCase:
    def __init__(self, testenv, folder):
        self.testenv = testenv
        self.test_folder = folder

        self.directory_error = False
        self.data_collected = False
        self.already_exists = False
        self.is_skip_test = False

        self.h1 = 'TESTCASE %s' % self.test_folder
        self.h2 = None

        self.check_folder()

    def traffic(self, traffic_fn, **kwargs):
        """
        Calls a given traffic generator with testcase specific details

        See traffic.py for more details
        """
        return traffic_fn(
            dry_run=self.testenv.dry_run,
            testbed=self.testenv.testbed,
            hint_fn=self.save_hint,
            run_fn=functools.partial(self.testenv.run, bg=True),
            **kwargs,  # pass on any custom arguments
        )

    def save_hint(self, text):
        logger.debug("hint(test): " + text)

        if not self.testenv.dry_run:
            save_hint_to_folder(self.test_folder, text)

    def log_header(self):
        """
        Must be called after check_folder()
        """
        out = '=' * len(self.h1) + ((' ' + '-' * len(self.h2)) if self.h2 is not None else '') + '\n'
        out += self.h1 + ((' ' + self.h2) if self.h2 is not None else '') + '\n'
        out += '=' * len(self.h1) + ((' ' + '-' * len(self.h2)) if self.h2 is not None else '') + '\n'
        out += str(datetime.now()) + '\n'
        logger.info(out)

    def check_folder(self):
        if os.path.exists(self.test_folder):
            if not os.path.isfile(self.test_folder + '/details'):
                self.h2 = 'Skipping existing and UNRECOGNIZED testcase directory'
                self.directory_error = True
                return
            else:
                if not self.testenv.retest:
                    with open(self.test_folder + '/details') as f:
                        for line in f:
                            if line.strip() == 'data_collected':
                                self.h2 = 'Using existing data'
                                self.already_exists = True
                                return

                    # clean up previous run
                    self.h2 = 'Rerunning incomplete test'
                else:
                    self.h2 = 'Repeating existing test'

        if self.testenv.skip_test:
            self.h2 = 'Skipping testcase because environment tells us to'
            self.is_skip_test = True

    def run_ta(self, bg=False):
        net_c = re.sub(r'\.[0-9]+$', '.0', os.environ['IP_AQM_C'])
        net_sa = re.sub(r'\.[0-9]+$', '.0', os.environ['IP_AQM_SA'])
        net_sb = re.sub(r'\.[0-9]+$', '.0', os.environ['IP_AQM_SB'])

        pcapfilter = 'ip and dst net %s/24 and (src net %s/24 or src net %s/24) and (tcp or udp)' % (net_c, net_sa, net_sb)

        cmd = bash[
            '-c',
            """
            # running analyzer
            set -e
            source aqmt-vars.sh
            mkdir -p '%s/ta'
            sudo %s $IFACE_CLIENTS '%s' '%s/ta' %d %d
            """ % (
                self.test_folder,
                os.path.join(os.path.dirname(__file__), 'ta/analyzer'),
                pcapfilter,
                self.test_folder,
                self.testenv.testbed.ta_delay,
                self.testenv.testbed.ta_samples + self.testenv.testbed.get_ta_samples_to_skip(),
            )
        ]

        logger.debug(get_log_cmd(cmd))
        if self.testenv.dry_run:
            pid = -1
        else:
            pid = self.testenv.run(cmd, bg=bg)

            # we add it to the kill list in case the script is terminated
            processes.add_known_pid(pid)

        return pid

    def calc_post_wait_time(self):
        """The time it will idle after the test is run"""
        return max(self.testenv.testbed.rtt_clients, self.testenv.testbed.rtt_servera, self.testenv.testbed.rtt_serverb) / 1000 * 5 + 2

    def calc_estimated_run_time(self):
        """
        Add one second for various delay.
        Note the time excludes any time used in pre/post hooks as it is unknown.
        """
        samples = self.testenv.testbed.ta_samples + self.testenv.testbed.get_ta_samples_to_skip()
        return samples * self.testenv.testbed.ta_delay / 1000 + self.calc_post_wait_time() + 1

    def run(self, test_fn, pre_hook=None, post_hook=None):
        if self.directory_error:
            raise Exception('Cannot run a test with an unrecognized directory')
        if self.data_collected:
            raise Exception('Cannot run the same TestCase multiple times')

        if not self.testenv.dry_run:
            if os.path.exists(self.test_folder):
                shutil.rmtree(self.test_folder)
            os.makedirs(self.test_folder, exist_ok=True)

        start = time.time()
        self.save_hint('type test')

        if not self.testenv.testbed.reset(dry_run=self.testenv.dry_run):
            raise Exception('Reset failed')
        logger.info('%.2f s: Testbed reset' % (time.time()-start))

        if not self.testenv.testbed.setup(dry_run=self.testenv.dry_run):
            raise Exception('Setup failed')
        if not self.testenv.dry_run:
            logger.info(self.testenv.testbed.get_setup())

        if pre_hook is not None and not self.testenv.dry_run:
            pre_hook(self)

        logger.info('%.2f s: Testbed initialized, starting test. Estimated time to finish: %d s' % (time.time()-start, self.calc_estimated_run_time()))

        self.save_hint('ta_idle %s' % self.testenv.testbed.ta_idle)
        self.save_hint('ta_delay %s' % self.testenv.testbed.ta_delay)
        self.save_hint('ta_samples %s' % self.testenv.testbed.ta_samples)
        self.save_hint('ta_samples_pre %s' % self.testenv.testbed.get_ta_samples_to_skip())

        hint = self.testenv.testbed.get_hint(dry_run=self.testenv.dry_run)
        for line in hint.split('\n'):
            self.save_hint(line)

        set_pid_ta(self.run_ta(bg=not self.testenv.is_interactive))

        if self.testenv.is_interactive and not self.testenv.dry_run:
            self.testenv.run_monitor_setup()
            self.testenv.run_speedometer(self.testenv.testbed.bitrate * 1.1, delay=0.05)

        test_fn(self)

        if not self.testenv.dry_run:
            processes.waitpid(get_pid_ta())  # wait until 'ta' quits
        set_pid_ta(None)

        logger.info('%.2f s: Data collection finished' % (time.time()-start))

        if post_hook is not None and not self.testenv.dry_run:
            post_hook(self)

        processes.kill_known_pids()

        if processes.is_exiting:
            print("You have aborted an active test")
            print("In 5 seconds we will store the results of it")
            print("Press Ctrl+C again NOW to not store the test")
            time.sleep(5)
            # if Ctrl+C is pressed here, we will be killed by a hook in TestEnv

        self.save_hint('data_collected')
        self.data_collected = True

        if not self.testenv.testbed.reset(dry_run=self.testenv.dry_run):
            raise Exception('Reset failed')
        logger.info('%.2f s: Testbed reset, waiting %.2f s for cooldown period' % (time.time()-start, self.calc_post_wait_time()))

        # in case there is a a queue buildup it should now free because the
        # testbed is reset (so no added RTT or rate limit) and we give it some
        # time to complete
        time.sleep(self.calc_post_wait_time())
        logger.info('%.2f s: Finished waiting to let the connections finish' % (time.time()-start))

        self.testenv.get_terminal().cleanup()

    def should_skip(self):
        return self.directory_error or self.data_collected or self.already_exists or self.is_skip_test

    def has_valid_data(self):
        return self.already_exists or (not self.testenv.dry_run and self.data_collected)

    def already_analyzed(self):
        if not os.path.isfile(self.test_folder + '/details'):
            return False

        with open(self.test_folder + '/details') as f:
            for line in f:
                if line.strip() == 'data_analyzed':
                    return True

        return False


    def analyze(self, analyze_fn):
        samples_to_skip = self.testenv.testbed.get_ta_samples_to_skip()

        remove_hint(self.test_folder, ['data_analyzed', 'analyzed_aggregated_samples_skipped'])

        analyze_fn(self, samples_to_skip)

        self.save_hint('data_analyzed')
        self.save_hint('analyzed_aggregated_samples_skipped %d' % samples_to_skip)
