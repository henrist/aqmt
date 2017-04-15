"""
This module contains the test environment logic

It does not include the testbed configuration, but things
around the testbed for running the actual tests.
"""

import os
from plumbum import local
import signal
import sys

from . import logger
from . import processes
from .terminal import Terminal, Tmux, get_log_cmd

pid_ta = None


def get_pid_ta():
    return pid_ta


def set_pid_ta(new_pid):
    global pid_ta
    pid_ta = new_pid


def remove_hint(folder, hint_names=None):
    if hint_names is None:
        hint_names = []
    file = folder + '/details'
    if os.path.isfile(file):
        if hint_names is None or len(hint_names) == 0:
            os.remove(file)
        else:
            with open(file, 'r+') as f:
                old = f.readlines()
                f.seek(0)
                for line in old:
                    if not line.split(maxsplit=1)[0] in hint_names:
                        f.write(line)
                f.truncate()


def save_hint_to_folder(folder, text):
    os.makedirs(folder, exist_ok=True)

    with open(folder + '/details', 'a') as f:
        f.write(text + '\n')


def read_metadata(file):
    """
    Reads metadata from a `details` file

    Returns a map of the properties as well as a list of properties to be used
    if properties of the same key is repeated
    """
    if not os.path.isfile(file):
        raise Exception('Missing metadata file: ' + file)

    metadata = {}
    lines = []

    with open(file, 'r') as f:
        for line in f:
            s = line.split(maxsplit=1)
            key = s[0]
            value = s[1].strip() if len(s) > 1 else ''
            metadata[key.strip()] = value
            lines.append((key, value))

    return metadata, lines


class TestEnv:
    def __init__(self, testbed, is_interactive=None, dry_run=False, reanalyze=False, replot=False, retest=False, skip_test=False):
        """
        skip_test: Will skip the test as if it already exists
        """
        self.testbed = testbed

        self.tests = []  # list of tests that has been run
        self.terminal = None

        if is_interactive is None:
            is_interactive = 'TEST_INTERACTIVE' in os.environ and os.environ['TEST_INTERACTIVE']  # run in tmux or not
        self.is_interactive = is_interactive
        self.dry_run = dry_run
        self.reanalyze = reanalyze
        self.replot = replot
        self.retest = retest
        self.skip_test = skip_test

        def exit_gracefully(signum, frame):
            if get_pid_ta() is not None:
                # we are running analyzer - let us terminate it but have its caller clean up
                processes.is_exiting = True
                processes.kill_pid(get_pid_ta())

            else:
                processes.kill_known_pids()
                self.get_terminal().cleanup()
                sys.exit()

        signal.signal(signal.SIGINT, exit_gracefully)
        signal.signal(signal.SIGTERM, exit_gracefully)

    def get_terminal(self):
        if self.terminal is None:
            self.terminal = Tmux() if self.is_interactive else Terminal()
        return self.terminal

    def run(self, cmd, bg=False):
        if bg:
            return self.get_terminal().run_bg(cmd)
        else:
            return self.get_terminal().run_fg(cmd)

    def run_speedometer(self, max_bitrate, delay=0.5):
        max_bitrate = max_bitrate / 8

        cmd = local['speedometer']['-s', '-i', '%f' % delay, '-l', '-t', os.environ['IFACE_CLIENTS'], '-m', '%d' % max_bitrate]

        logger.debug(get_log_cmd(cmd))
        if not self.dry_run:
            pid = self.run(cmd)
            processes.add_known_pid(pid)

    def run_monitor_setup(self):
        cmd = local['watch']['-n', '.2', './views/show_setup.sh', '-v', '%s' % os.environ['IFACE_CLIENTS']]

        logger.info(get_log_cmd(cmd))
        if not self.dry_run:
            pid = self.run(cmd)
            processes.add_known_pid(pid)
