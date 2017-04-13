#!/usr/bin/env python3

"""Henrik's test framework

For interactive tests (with live plots), run:
$ TEST_INTERACTIVE=1 ./mytest.py

For increased logging, run:
$ LOG_LEVEL=DEBUG ./mytest.py

"""

import time
import datetime
import errno
import os
import signal
import sys
import time
import plumbum
import io
import types
import re
import shutil
import functools
from plumbum import local, FG, BG
from plumbum.cmd import bash, tmux, ssh
from plumbum.commands.processes import ProcessExecutionError
import subprocess

from .calc_queuedelay import QueueDelay
from .calc_tagged_rate import TaggedRate
from .calc_utilization import Utilization
from .plot import Plot

is_exiting = False
pid_ta = None

def get_common_script_path():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/common.sh'

def get_shell_cmd(cmd_object):
    """Convert a plumbum cmd to a shell expression"""
    return ' '.join(cmd_object.formulate(10))

def require_on_aqm_node():
    common = get_common_script_path()
    bash['-c', 'set -e; source %s; require_on_aqm_node' % common] & FG

def kill_known_pids():
    if not hasattr(kill_known_pids, 'pids'):
        return

    for pid in kill_known_pids.pids:
        kill_pid(pid)

    kill_known_pids.pids = []

def add_known_pid(pid):
    if not hasattr(kill_known_pids, 'pids'):
        kill_known_pids.pids = []

    kill_known_pids.pids.append(pid)

def kill_pid(pid):
    try:
        os.kill(pid, signal.SIGTERM)
        Logger.trace('Sent SIGTERM to PID %d' % pid)
    except ProcessLookupError:
        pass

def is_running(pid):
    try:
        os.kill(pid, 0)
    except OSError as err:
        if err.errno == errno.ESRCH:
            return False
    return True

def waitpid(pid):
    # due to some issues when running child process vs tmux this is a bit more complex
    # first use os.waitpid in case this is a child of current process
    try:
        os.waitpid(pid, 0)
    except ChildProcessError:
        pass

    while is_running(pid):
        time.sleep(0.3)

def get_log_cmd(cmd, prefix = 'SHELL: '):
    if not isinstance(cmd, str):
        cmd = get_shell_cmd(cmd)
    return '%s %s' % (prefix, cmd)

class Logger():
    TRACE = 4
    DEBUG = 3
    INFO = 2
    WARN = 1
    ERROR = 0

    NAME_TABLE = {
        'TRACE': TRACE,
        'DEBUG': DEBUG,
        'INFO': INFO,
        'WARN': WARN,
        'ERROR': ERROR,
    }

    @staticmethod
    def get_level_from_name(level_name, name_table, default):
        if level_name in name_table:
            return name_table[level_name]
        return default

    print_level = get_level_from_name.__func__(
        os.environ['LOG_LEVEL'] if 'LOG_LEVEL' in os.environ else '',
        NAME_TABLE,
        INFO
    )
    file_level = TRACE
    logfile = os.environ['LOG_FILE'] if 'LOG_FILE' in os.environ else 'test_framework.log'

    @classmethod
    def get_level_name(cls, level):
        if level == cls.TRACE: return 'TRACE'
        if level == cls.DEBUG: return 'DEBUG'
        if level == cls.INFO: return 'INFO'
        if level == cls.WARN: return 'WARN'
        if level == cls.ERROR: return 'ERROR'
        return 'UNKNOWN'

    @classmethod
    def trace(cls, msg):
        cls.log(cls.TRACE, msg)

    @classmethod
    def debug(cls, msg):
        cls.log(cls.DEBUG, msg)

    @classmethod
    def info(cls, msg):
        cls.log(cls.INFO, msg)

    @classmethod
    def warn(cls, msg):
        cls.log(cls.WARN, msg)

    @classmethod
    def error(cls, msg):
        cls.log(cls.ERROR, msg)

    @classmethod
    def log(cls, level, msg):
        if level <= cls.print_level:
            print(msg)

        if level <= cls.file_level and cls.logfile is not None:
            with open(cls.logfile, 'a') as f:
                level_name = cls.get_level_name(level)
                prefix = '%s %7s: ' % (datetime.datetime.now().isoformat(), level_name)
                f.write(cls.prefix_multiline(prefix, msg, '\n'))

    @staticmethod
    def prefix_multiline(prefix, msg, append=''):
        return prefix + msg.replace('\n', '\n' + ' ' * len(prefix)) + append


class Terminal():
    def __init__(self):
        pass

    def cleanup(self):
        pass

    def run_fg(self, cmd):
        cmd = get_shell_cmd(cmd)
        p = bash['-c', cmd].popen(stdin=None, stdout=None, stderr=None, close_fds=True)

        Logger.trace('RUN_FG (PID: %d): %s' % (p.pid, get_log_cmd(cmd, prefix='')))
        return p.pid

    def run_bg(self, cmd):
        cmd = get_shell_cmd(cmd)
        p = bash['-c', cmd].popen(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)

        Logger.trace('RUN_BG (PID: %d): %s' % (p.pid, get_log_cmd(cmd, prefix='')))
        return p.pid


class Tmux(Terminal):
    def __init__(self):
        if 'TMUX' not in os.environ:
            raise Exception("Please run this inside a tmux session")

        self.win_id = tmux['display-message', '-p', '-t', os.environ['TMUX_PANE'], '#{window_id}']().strip()
        self.session_id = tmux['display-message', '-p', '-t', os.environ['TMUX_PANE'], '#{session_id}']().strip()
        self.win_bg_id = None

        tmux['set-window-option', '-t', self.win_id, 'remain-on-exit', 'on']()
        self.cleanup()

    def cleanup(self):
        self.kill_dead_panes()

    def kill_dead_panes(self):
        (tmux['list-panes', '-s', '-F', '#{pane_dead} #{pane_id}', '-t', self.session_id] | local['grep']['^1'] | local['awk']['{print $2}'] | local['xargs']['-rL1', 'tmux', 'kill-pane', '-t']).run(retcode=None)

    def get_pane_id(self, window_id):
        # for some reasons list-panes is not reliable with -t flag
        # so list everything and find from it
        pane_ids = (tmux['list-panes', '-aF', '#{window_id} #{pane_id}'] | local['grep']['^' + window_id + ' '] | local['awk']['{ print $2 }']).run(retcode=None)[1].split()
        return pane_ids[0]

    def run_fg(self, cmd):
        cmd = get_shell_cmd(cmd)
        pane_pid = tmux['split-window', '-dP', '-t', self.get_pane_id(self.win_id), '-F', '#{pane_pid}', cmd]().strip()

        tmux['select-layout', '-t', self.win_id, 'tiled']()

        Logger.trace('RUN_FG (TMUX PID: %d): %s' % (pane_pid, get_log_cmd(cmd, prefix='')))
        return int(pane_pid)

    def run_bg(self, cmd):
        cmd = get_shell_cmd(cmd)

        # create the window if needed
        # output in the end should be the new pid of the running command
        # so that we can stop it later
        if not self.have_bg_win():
            res = tmux['new-window', '-adP', '-F', '#{window_id} #{pane_pid}', '-t', self.win_id, cmd]().strip().split()
            self.win_bg_id = res[0]
            pane_pid = res[1]
            tmux['set-window-option', '-t', self.win_bg_id, 'remain-on-exit', 'on'] & FG

        else:
            pane_pid = tmux['split-window', '-dP', '-t', self.get_pane_id(self.win_bg_id), '-F', '#{pane_pid}', cmd]().strip()
            tmux['select-layout', '-t', self.win_bg_id, 'tiled'] & FG

        Logger.trace('RUN_BG (TMUX PID: %d): %s' % (pane_pid, get_log_cmd(cmd, prefix='')))
        return int(pane_pid)

    def have_bg_win(self):
        if self.win_bg_id == None:
            return False

        res = (tmux['list-windows', '-aF', '#{window_id}'] | local['grep']['^' + self.win_bg_id + '$']).run(retcode=None)[1].strip()

        return len(res) > 0


class Testbed():
    ECN_DISABLED = 0
    ECN_INITIATE = 1
    ECN_ALLOW = 2

    def __init__(self):
        self.bitrate = 1000000

        self.rtt_clients = 0  # in ms
        self.rtt_servera = 0  # in ms
        self.rtt_serverb = 0  # in ms

        self.netem_clients_params = ""
        self.netem_servera_params = ""
        self.netem_serverb_params = ""

        self.aqm_name = ''
        self.aqm_params = ''

        self.cc_a = 'cubic'
        self.ecn_a = self.ECN_ALLOW
        self.cc_b = 'cubic'
        self.ecn_b = self.ECN_ALLOW

        self.ta_idle = None  # time to wait before collecting traffic, default to RTT-dependent
        self.ta_delay = 1000
        self.ta_samples = 250

        self.traffic_port = 5500

    def aqm(self, name='', params=''):
        if name == 'pfifo':
            name = 'pfifo_qsize' # use our custom version with qsize

        self.aqm_name = name
        self.aqm_params = params

    def cc(self, node, cc, ecn):
        if node != 'a' and node != 'b':
            raise Exception("Invalid node: %s" % node)

        if node == 'a':
            self.cc_a = cc
            self.ecn_a = ecn
        else:
            self.cc_b = cc
            self.ecn_b = ecn

    def get_ta_idle(self):
        if self.ta_idle is None:
            return (max(self.rtt_clients, self.rtt_servera, self.rtt_serverb) / 1000) * 20 + 3
        return self.ta_idle

    def setup(self, dry_run=False, log_level=Logger.DEBUG):
        cmd = bash['-c', """
            # configuring testbed
            set -e
            source """ + get_common_script_path() + """

            set_offloading off

            configure_clients_edge """ + '%s %s %s "%s" "%s"' % (self.bitrate, self.rtt_clients, self.aqm_name, self.aqm_params, self.netem_clients_params) + """
            configure_server_edge $IP_SERVERA_MGMT $IP_AQM_SA $IFACE_SERVERA $IFACE_ON_SERVERA """ + '%s "%s"' % (self.rtt_servera, self.netem_servera_params) + """
            configure_server_edge $IP_SERVERB_MGMT $IP_AQM_SB $IFACE_SERVERB $IFACE_ON_SERVERB """ + '%s "%s"' % (self.rtt_serverb, self.netem_serverb_params) + """

            configure_host_cc $IP_CLIENTA_MGMT """ + '%s %s' % (self.cc_a, self.ecn_a) + """
            configure_host_cc $IP_SERVERA_MGMT """ + '%s %s' % (self.cc_a, self.ecn_a) + """
            configure_host_cc $IP_CLIENTB_MGMT """ + '%s %s' % (self.cc_b, self.ecn_b) + """
            configure_host_cc $IP_SERVERB_MGMT """ + '%s %s' % (self.cc_b, self.ecn_b) + """
            """]

        Logger.log(log_level, get_log_cmd(cmd))
        if not dry_run:
            try:
                cmd & FG
            except ProcessExecutionError:
                return False

        return True

    def reset(self, dry_run=False, log_level=Logger.DEBUG):
        cmd = bash['-c', """
            # resetting testbed
            set -e
            source """ + get_common_script_path() + """

            kill_all_traffic
            reset_aqm_client_edge
            reset_aqm_server_edge
            reset_all_hosts_edge
            reset_all_hosts_cc
            """]

        Logger.log(log_level, get_log_cmd(cmd))
        if not dry_run:
            try:
                cmd & FG
            except ProcessExecutionError:
                return False

        return True

    def get_next_traffic_port(self):
        tmp = self.traffic_port
        self.traffic_port += 1
        return tmp

    @staticmethod
    def get_aqm_options(name):
        common = get_common_script_path()
        res = bash['-c', 'set -e; source %s; get_aqm_options %s' % (common, name)]()
        return res.strip()

    def get_setup(self):
        out = ""

        out += "Configured testbed:\n"
        out += "  rate: %s (applied from router to clients)\n" % self.bitrate
        out += "  rtt to router:\n"
        out += "    - clients: %d ms\n" % self.rtt_clients
        out += "    - servera: %d ms\n" % self.rtt_servera
        out += "    - serverb: %d ms\n" % self.rtt_serverb

        if self.aqm_name != '':
            params = ''
            if self.aqm_params != '':
                params = ' (%s)' % self.aqm_params

            out += "  aqm: %s%s\n" % (self.aqm_name, params)
            out += "       (%s)\n" % self.get_aqm_options(self.aqm_name)
        else:
            out += "  no aqm\n"

        for node in ['CLIENTA', 'CLIENTB', 'SERVERA', 'SERVERB']:
            ip = 'IP_%s_MGMT' % node

            out += '  %s: ' % node.lower()
            common = get_common_script_path()
            out += (bash['-c', 'set -e; source %s; get_host_cc "$%s"' % (common, ip)] | local['tr']['\n', ' '])().strip()
            out += '\n'

        return out.strip()

    @staticmethod
    def analyze_results(testfolder, dry_run=False, log_level=Logger.DEBUG):
        if dry_run:
            Logger.warn("Cannot determine bitrate in dry run mode, setting to -1")
            bitrate = -1

        else:
            bitrate = 0
            with open(testfolder + '/details', 'r') as f:
                for line in f:
                    if line.startswith('testbed_rate'):
                        bitrate = int(line.split()[1])
                        break

            if bitrate == 0:
                raise Exception("Could not determine bitrate of test '%s'" % testfolder)

        rtt_l4s = 0            # used to calculate window size, we don't use it now
        rtt_classic = 0        # used to calculate window size, we don't use it now

        if not os.path.exists(testfolder + '/derived'):
            os.makedirs(testfolder + '/derived')

        cmd = local['./framework/calc_basic'][testfolder + '/ta', testfolder + '/derived', str(bitrate), str(rtt_l4s), str(rtt_classic)]
        Logger.log(log_level, get_log_cmd(cmd))

        if dry_run:
            Logger.warn("Skipping post processing due to dry run")

        else:
            cmd()

            start = time.time()

            qd = QueueDelay()
            qd.processTest(testfolder)

            tr = TaggedRate()
            tr.processTest(testfolder)

            u = Utilization()
            u.processTest(testfolder, bitrate)

    def get_hint(self, dry_run=False):
        hint = ''
        hint += "testbed_rtt_clients %d\n" % self.rtt_clients
        hint += "testbed_rtt_servera %d\n" % self.rtt_servera
        hint += "testbed_rtt_serverb %d\n" % self.rtt_serverb
        hint += "testbed_cc_a %s %d\n" % (self.cc_a, self.ecn_a)
        hint += "testbed_cc_b %s %d\n" % (self.cc_b, self.ecn_b)
        hint += "testbed_aqm %s\n" % self.aqm_name
        hint += "testbed_aqm_params %s\n" % self.aqm_params
        if dry_run:
            hint += "testbed_aqm_params_full UNKNOWN IN DRY RUN\n"
        else:
            hint += "testbed_aqm_params_full %s\n" % self.get_aqm_options(self.aqm_name)
        hint += "testbed_rate %s\n" % self.bitrate
        return hint.strip()


class TestCase():
    def __init__(self, testenv, folder):
        self.testenv = testenv
        self.test_folder = folder

        self.directory_error = False
        self.data_collected = False
        self.already_exists = False
        self.is_skip_test = False

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
            run_fn=self.testenv.run,
            **kwargs,  # pass on any custom arguments
        )

    def save_hint(self, text):
        Logger.debug("hint(test): " + text)

        if not self.testenv.dry_run:
            TestEnv.save_hint_to_folder(self.test_folder, text)

    def log_header(self):
        """
        Must be called after check_folder()
        """
        out = '=' * len(self.h1) + ((' ' + '-' * len(self.h2)) if self.h2 is not None else '') + '\n'
        out += self.h1 + ((' ' + self.h2) if self.h2 is not None else '') + '\n'
        out += '=' * len(self.h1) + ((' ' + '-' * len(self.h2)) if self.h2 is not None else '') + '\n'
        out += str(datetime.datetime.now()) + '\n'
        Logger.info(out)

    def check_folder(self):
        self.h1 = 'TESTCASE %s' % self.test_folder
        self.h2 = None

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
                                self.already_exists = True
                                return

                    # clean up previous run
                    self.h2 = 'Rerunning incomplete test'
                else:
                    self.h2 = 'Repeating existing test'

        if self.testenv.skip_test:
            h2 = 'Skipping testcase because environment tells us to'
            self.is_skip_test = True

    def run_ta(self, bg=False):
        net_c = re.sub(r'\.[0-9]+$', '.0', os.environ['IP_AQM_C'])
        net_sa = re.sub(r'\.[0-9]+$', '.0', os.environ['IP_AQM_SA'])
        net_sb = re.sub(r'\.[0-9]+$', '.0', os.environ['IP_AQM_SB'])

        pcapfilter = 'ip and dst net %s/24 and (src net %s/24 or src net %s/24) and (tcp or udp)' % (net_c, net_sa, net_sb)
        ipclass = 'f'

        cmd = bash[
            '-c',
            """
            # running analyzer
            set -e
            echo 'Idling a bit before running analyzer...'
            sleep %f
            . vars.sh
            mkdir -p '%s'
            sudo ./framework/ta/analyzer $IFACE_CLIENTS '%s' '%s/ta' %d %s %d
            """ % (
                self.testenv.testbed.get_ta_idle(),
                self.test_folder,
                pcapfilter,
                self.test_folder,
                self.testenv.testbed.ta_delay,
                ipclass,
                self.testenv.testbed.ta_samples
            )
        ]

        Logger.debug(get_log_cmd(cmd))
        if self.testenv.dry_run:
            pid = -1
        else:
            pid = self.testenv.run(cmd, bg=bg)

            # we add it to the kill list in case the script is terminated
            add_known_pid(pid)

        return pid

    def calc_post_wait_time(self):
        """The time it will idle after the test is run"""
        return max(self.testenv.testbed.rtt_clients, self.testenv.testbed.rtt_servera, self.testenv.testbed.rtt_serverb) / 1000 * 5 + 2

    def calc_estimated_run_time(self):
        # add one second for various delay
        return self.testenv.testbed.ta_samples * self.testenv.testbed.ta_delay / 1000 + self.testenv.testbed.get_ta_idle() + self.calc_post_wait_time() + 1

    def run(self, test_fn):
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
        Logger.info('%.2f s: Testbed reset' % (time.time()-start))

        if not self.testenv.testbed.setup(dry_run=self.testenv.dry_run):
            raise Exception('Setup failed')
        if not self.testenv.dry_run:
            Logger.info(self.testenv.testbed.get_setup())

        Logger.info('%.2f s: Testbed initialized, starting test. Estimated time to finish: %d s' % (time.time()-start, self.calc_estimated_run_time()))

        self.save_hint('ta_idle %s' % self.testenv.testbed.get_ta_idle())
        self.save_hint('ta_delay %s' % self.testenv.testbed.ta_delay)
        self.save_hint('ta_samples %s' % self.testenv.testbed.ta_samples)

        hint = self.testenv.testbed.get_hint(dry_run=self.testenv.dry_run)
        for line in hint.split('\n'):
            self.save_hint(line)

        global pid_ta
        pid_ta = self.run_ta(bg=not self.testenv.is_interactive)

        if self.testenv.is_interactive and not self.testenv.dry_run:
            self.testenv.run_monitor_setup()
            self.testenv.run_speedometer(self.testenv.testbed.bitrate * 1.1, delay=0.05)

        test_fn(self)

        if not self.testenv.dry_run:
            waitpid(pid_ta)  # wait until 'ta' quits

        pid_ta = None
        kill_known_pids()

        Logger.info('%.2f s: Data collection finished' % (time.time()-start))
        self.save_hint('data_collected')
        self.data_collected = True

        if not self.testenv.testbed.reset(dry_run=self.testenv.dry_run):
            raise Exception('Reset failed')
        Logger.info('%.2f s: Testbed reset, waiting %.2f s for cooldown period' % (time.time()-start, self.calc_post_wait_time()))

        # in case there is a a queue buildup it should now free because the
        # testbed is reset (so no added RTT or rate limit) and we give it some
        # time to complete
        time.sleep(self.calc_post_wait_time())
        Logger.info('%.2f s: Finished waiting to let the connections finish' % (time.time()-start))

        self.testenv.get_terminal().cleanup()

    def should_skip(self):
        return self.directory_error or self.data_collected or self.already_exists or self.is_skip_test

    def has_valid_data(self):
        return self.already_exists or (not self.testenv.dry_run and self.data_collected)

    def analyze(self):
        TestEnv.remove_hint(self.test_folder, ['data_analyzed'])
        Testbed.analyze_results(self.test_folder, dry_run=self.testenv.dry_run)
        self.save_hint('data_analyzed')

    def plot(self):
        p = Plot()
        p.plot_flow(self.test_folder)


class TestEnv():
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
            if pid_ta is not None:
                # we are running analyzer - let us terminate it but have its caller clean up
                global is_exiting
                is_exiting = True
                kill_pid(pid_ta)

            else:
                kill_known_pids()
                self.get_terminal().cleanup()
                sys.exit()

        signal.signal(signal.SIGINT, exit_gracefully)
        signal.signal(signal.SIGTERM, exit_gracefully)

    def get_terminal(self):
        if self.terminal == None:
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

        Logger.debug(get_log_cmd(cmd))
        if not self.dry_run:
            pid = self.run(cmd)
            add_known_pid(pid)

    def run_monitor_setup(self):
        cmd = local['watch']['-n', '.2', './views/show_setup.sh', '-v', '%s' % os.environ['IFACE_CLIENTS']]

        Logger.info(get_log_cmd(cmd))
        if not self.dry_run:
            pid = self.run(cmd)
            add_known_pid(pid)

    @staticmethod
    def save_hint_to_folder(folder, text):
        os.makedirs(folder, exist_ok=True)

        with open(folder + '/details', 'a') as f:
            f.write(text + '\n')

    @staticmethod
    def remove_hint(folder, hint_names=[]):
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


class TestCollection():
    """Organizes tests in collections and stores metadata used to automatically plot

    Test hierarchy looks like (from bottom up):
    - collection of a single test
    - collection of collections, and so on
    """

    def __init__(self, folder, title=None, subtitle=None, titlelabel=None, parent=None):
        if parent:
            self.folder = parent.folder + '/' + folder
            parent.check_and_add_tag(folder)
        else:
            self.folder = folder

        self.tags_used = []  # to make sure we have unique tags as children

        self.test = None
        self.collections = []

        self.parent = parent
        self.parent_called = False

        self.hints_initialized = False  # defer initialization of hints till we have data
        self.title = title
        self.subtitle = subtitle
        self.titlelabel = titlelabel


    def check_and_add_tag(self, tag):
        """
        This ensures we don't have duplicate tags in the collection
        """
        if tag in self.tags_used:
            raise Exception("Tag must be unique inside same collection (tag: %s)" % tag)

        self.tags_used.append(tag)

    def add_child(self, child_folder):
        """
        Add a child of this collection.

        It can be another collection (then this is called by the child
        collection itself), or a single test.

        The start of call chain for this is a test that has data.
        If no tests with data are inside this collection, it will
        never be visible in folder structure.
        """
        if not self.hints_initialized:
            self.hints_initialized = True
            TestEnv.remove_hint(self.folder)
            TestEnv.save_hint_to_folder(self.folder, 'type collection')

            if self.title is not None:
                TestEnv.save_hint_to_folder(self.folder, 'title %s' % self.title)

            if self.subtitle is not None:
                TestEnv.save_hint_to_folder(self.folder, 'subtitle %s' % self.subtitle)

            if self.titlelabel is not None:
                TestEnv.save_hint_to_folder(self.folder, 'titlelabel %s' % self.titlelabel)

        TestEnv.save_hint_to_folder(self.folder, 'sub %s' % child_folder)

        if self.parent and not self.parent_called:
            self.parent_called = True
            self.parent.collections.append(self)
            self.parent.add_child(os.path.basename(self.folder))

    def run_test(self, test_fn, testenv):
        """
        Run a single test (the smallest possible test)

        test_fn: Method that generates test data
        """

        if self.test:
            raise Exception("A collection cannot contain multiple tests")

        test_folder = 'test'

        self.test = TestCase(testenv=testenv, folder=self.folder + '/' + test_folder)
        self.test.log_header()

        if not self.test.should_skip():
            self.test.run(test_fn)

        if (self.test.data_collected or self.test.already_exists) and not testenv.dry_run:
            if testenv.reanalyze or not self.test.already_exists:
                start = time.time()
                self.test.analyze()
                Logger.info('Analyzed test (%.2f s)' % (time.time()-start))

            if testenv.reanalyze or testenv.replot or not self.test.already_exists:
                start = time.time()
                self.test.plot()
                Logger.info('Plotted test (%.2f s)' % (time.time()-start))

            self.add_child(test_folder)

        elif self.test.already_exists:
            self.add_child(test_folder)

        # if we have received a SIGTERM we will terminate TA but allow the plotting
        global is_exiting
        if is_exiting:
            kill_known_pids()
            testenv.get_terminal().cleanup()
            sys.exit()

    def get_metadata(self, testenv):
        """
        Instead of running the test, this method can be called
        to generate various metedata without actually running the test.
        """
        test = TestCase(testenv=testenv, folder=self.folder + '/test')
        return {
            'estimated_time': test.calc_estimated_run_time(),
            'will_test': not test.should_skip(),
        }


if __name__ == '__main__':
    print("This script is not to be run directly but used by other tests")
