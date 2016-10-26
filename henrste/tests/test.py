#!/usr/bin/env python3

"""Henrik's test framework

For interactive tests (with live plots), run:
$ TEST_INTERACTIVE=1 ./test.py

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
import subprocess

from calc_queuedelay import QueueDelay
from calc_utilization import Utilization
from plot import Plot, plot_folder_compare, plot_folder_flows

def get_shell_cmd(cmd_object):
    """Convert a plumbum cmd to a shell expression"""
    return ' '.join(cmd_object.formulate(10))

def require_on_aqm_node():
    bash['-c', 'source ../common.sh; require_on_aqm_node'] & FG

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

class Terminal():
    def __init__(self):
        pass

    def cleanup(self):
        pass

    def run_fg(self, cmd, verbose=False):
        cmd = get_shell_cmd(cmd)
        if verbose:
            print(cmd)

        p = bash['-c', cmd].popen(stdin=None, stdout=None, stderr=None, close_fds=True)
        return p.pid

    def run_bg(self, cmd, verbose=False):
        cmd = get_shell_cmd(cmd)
        if verbose:
            print(cmd)

        p = bash['-c', cmd].popen(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
        return p.pid


class Tmux(Terminal):
    win_id = None
    win_bg_id = None

    def __init__(self):
        if 'TMUX' not in os.environ:
            raise Exception("Please run this inside a tmux session")

        self.win_id = tmux['display-message', '-p', '#{window_id}']().strip()
        tmux['set-window-option', '-t', self.win_id, 'remain-on-exit', 'on']()

        self.cleanup()

    def cleanup(self):
        self.kill_dead_panes()

    def kill_dead_panes(self):
        (tmux['list-panes', '-s', '-F', '#{pane_dead} #{pane_id}'] | local['grep']['^1'] | local['awk']['{print $2}'] | local['xargs']['-rL1', 'tmux', 'kill-pane', '-t']).run(retcode=None)

    def run_fg(self, cmd, verbose=False):
        cmd = get_shell_cmd(cmd)
        if verbose:
            print(cmd)

        pane_pid = tmux['split-window', '-dP', '-t', self.win_id, '-F', '#{pane_pid}', cmd]().strip()

        tmux['select-layout', '-t', self.win_id, 'tiled']()
        return int(pane_pid)

    def run_bg(self, cmd, verbose=False):
        cmd = get_shell_cmd(cmd)
        if verbose:
            print(cmd)

        # create the window if needed
        # output in the end should be the new pid of the running command
        # so that we can stop it later
        if not self.have_bg_win():
            res = tmux['new-window', '-dP', '-F', '#{window_id} #{pane_pid}', cmd]().strip().split()
            self.win_bg_id = res[0]
            pane_pid = res[1]
            tmux['set-window-option', '-t', self.win_bg_id, 'remain-on-exit', 'on'] & FG

        else:
            pane_pid = tmux['split-window', '-dP', '-t', self.win_bg_id, '-F', '#{pane_pid}', cmd]().strip()
            tmux['select-layout', '-t', self.win_bg_id, 'tiled'] & FG

        return int(pane_pid)

    def have_bg_win(self):
        if self.win_bg_id == None:
            return False

        res = (tmux['list-windows', '-F', '#{window_id}'] | local['grep'][self.win_bg_id]).run(retcode=None)[1].strip()

        return len(res) > 0


class Testbed():
    def __init__(self):
        self.bitrate = 1000000
        self.rtt_clients = 0  # in ms
        self.rtt_servera = 0  # in ms
        self.rtt_serverb = 0  # in ms
        self.aqm_name = ''
        self.aqm_params = ''
        self.cc_a = 'cubic'
        self.ecn_a = 2  # 2 = allow ecn, 1 = force ecn, 0 = no ecn
        self.cc_b = 'cubic'
        self.ecn_b = 2

    def aqm_default(self):
        self.aqm_name = ''
        self.aqm_params = ''

    def aqm_pi2(self, params = '', params_append=True):
        self.aqm_name = 'pi2'
        if params_append:
            self.aqm_params = 'dualq limit 1000'  # l_thresh 10000"
        else:
            self.aqm_params = ''

        self.aqm_params += ' ' + str(params)


    def aqm_red(self):
        self.aqm_name = 'red'
        self.aqm_params = 'limit 1000000 avpkt 1000 ecn adaptive bandwidth %d' % self.bitrate

    def aqm_dualq(self):
        self.aqm_name = 'dualq'
        self.aqm_params = 'l_thresh_us 1000 offset 0 l_slope 5 c_slope 4 l_smooth 0 c_smooth 5 l_power 1 c_power 2 l_shift 50'

    def aqm_pie(self):
        self.aqm_name = 'pie'
        self.aqm_params = 'ecn'

    def aqm_fq_codel(self):
        self.aqm_name = 'fq_codel'
        self.aqm_params = 'ecn'

    def setup(self, dry_run=False, verbose=0):
        cmd = bash['-c', """
            source ../common.sh

            configure_clients_edge """ + '%s %s %s "%s"' % (self.bitrate, self.rtt_clients, self.aqm_name, self.aqm_params) + """
            configure_server_edge $IP_SERVERA_MGMT $IP_AQM_SA $IFACE_SERVERA $IFACE_ON_SERVERA """ + str(self.rtt_servera) + """
            configure_server_edge $IP_SERVERB_MGMT $IP_AQM_SB $IFACE_SERVERB $IFACE_ON_SERVERB """ + str(self.rtt_serverb) + """

            configure_host_cc $IP_CLIENTA_MGMT """ + '%s %s' % (self.cc_a, self.ecn_a) + """
            configure_host_cc $IP_SERVERA_MGMT """ + '%s %s' % (self.cc_a, self.ecn_a) + """
            configure_host_cc $IP_CLIENTB_MGMT """ + '%s %s' % (self.cc_b, self.ecn_b) + """
            configure_host_cc $IP_SERVERB_MGMT """ + '%s %s' % (self.cc_b, self.ecn_b) + """
            """]

        if dry_run:
            if verbose > 1:
                print(get_shell_cmd(cmd))
        else:
            cmd & FG


    def reset(self, dry_run=False, verbose=0):
        cmd = bash['-c', """
            source ../common.sh
            reset_aqm_client_edge
            reset_aqm_server_edge
            reset_all_hosts_edge
            reset_all_hosts_cc
            """]

        if dry_run:
            if verbose > 1:
                print(get_shell_cmd(cmd))
        else:
            cmd & FG

    @staticmethod
    def get_aqm_options(name):
        res = bash['-c', 'source ../common.sh; get_aqm_options %s' % name]()
        return res.strip()

    def print_setup(self):
        print("Configured testbed:")
        print("  rate: %s (applied from router to clients)" % self.bitrate)
        print("  rtt to router:")
        print("    - clients: %d ms" % self.rtt_clients)
        print("    - servera: %d ms" % self.rtt_servera)
        print("    - serverb: %d ms" % self.rtt_serverb)

        if self.aqm_name != '':
            params = ''
            if self.aqm_params != '':
                params = ' (%s)' % self.aqm_params

            print("  aqm: %s%s" % (self.aqm_name, params))
            print("       (%s)" % self.get_aqm_options(self.aqm_name))
        else:
            print("  no aqm")

        for node in ['CLIENTA', 'CLIENTB', 'SERVERA', 'SERVERB']:
            ip = 'IP_%s_MGMT' % node

            print('  %s: ' % node.lower(), end='')
            res = (bash['-c', 'source ../common.sh; get_host_cc "$%s"' % ip] | local['tr']['\n', ' '])().strip()
            print(res)

    @staticmethod
    def analyze_results(testfolder, dry_run=False, verbose=0):
        if dry_run:
            if verbose > 0:
                print("Cannot determine bitrate in dry run mode, setting to -1")
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

        fairness = "e"         # used to calculate rPDF, we don't use it now
        nbrf = 0               # used to calculate rPDF, we don't use it now
        rtt_l4s = 0            # used to calculate window size, we don't use it now
        rtt_classic = 0        # used to calculate window size, we don't use it now
        nbr_l4s_flows = 1      # used to generate rPDF and dmPDF, we don't use it now
        nbr_classic_flows = 1  # used to generate rPDF and dmPDF, we don't use it now

        cmd = local['../../traffic_analyzer/calc_henrste'][testfolder, fairness, str(nbrf), str(bitrate), str(rtt_l4s), str(rtt_classic), str(nbr_l4s_flows), str(nbr_classic_flows)]
        if verbose > 0:
            print(get_shell_cmd(cmd))

        if dry_run:
            if verbose > 0:
                print("Skipping post processing due to dry run")

        else:
            cmd()

            qd = QueueDelay()
            qd.processTest(testfolder)

            u = Utilization()
            u.processTest(testfolder, bitrate)

    def get_hint(self, dry_run=False, verbose=0):
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


class TestEnv():
    def __init__(self, set_folder):
        self.set_folder = set_folder

        self.skipped_last = False
        self.testnum = 0
        self.tags_used = []
        self.testfolders = []  # list of completed tests

        self.terminal = None
        self.is_interactive = 'TEST_INTERACTIVE' in os.environ and os.environ['TEST_INTERACTIVE']  # run in tmux or not
        self.ta_idle = 3  # time to wait before collecting traffic
        self.ta_delay = 1000
        self.ta_samples = 60
        self.traffic_port = 5500
        self.dry_run = False
        self.verbose = 1
        self.data_collected = False

        require_on_aqm_node()

        def exit_gracefully(signum, frame):
            kill_known_pids()
            self.get_terminal().cleanup()
            sys.exit()

        signal.signal(signal.SIGINT, exit_gracefully)
        signal.signal(signal.SIGTERM, exit_gracefully)

    def get_next_traffic_port(self):
        tmp = self.traffic_port
        self.traffic_port += 1
        return tmp

    def get_terminal(self):
        if self.terminal == None:
            self.terminal = Tmux() if self.is_interactive else Terminal()
        return self.terminal

    def run(self, cmd, bg=False, verbose=False):
        if bg:
            return self.get_terminal().run_bg(cmd, verbose=verbose)
        else:
            return self.get_terminal().run_fg(cmd, verbose=verbose)

    def run_greedy(self, node='a'):
        """
        Run greedy TCP traffic

        Greedy = always data to send, full frames

        node: a or b (a is normally classic traffic, b is normally l4s)

        Returns a lambda to stop the traffic
        """
        server_port = self.get_next_traffic_port()

        node = 'A' if node == 'a' else 'B'

        self.save_hint('traffic=tcp type=greedy node=%s%s server=%s' % (node, node, server_port))

        cmd1 = ssh['-tt', os.environ['IP_SERVER%s_MGMT' % node], '/opt/testbed/greedy_generator/greedy -vv -s %d' % server_port]
        cmd2 = ssh['-tt', os.environ['IP_CLIENT%s_MGMT' % node], 'sleep 0.2; /opt/testbed/greedy_generator/greedy -vv %s %d' % (os.environ['IP_SERVER%s' % node], server_port)]

        if self.dry_run:
            if self.verbose > 0:
                print(get_shell_cmd(cmd1))
                print(get_shell_cmd(cmd2))

            def stopTest():
                pass

        else:
            pid_server = self.run(cmd1, bg=True, verbose=True)
            pid_client = self.run(cmd2, bg=True, verbose=True)
            add_known_pid(pid_server)
            add_known_pid(pid_client)

            def stopTest():
                kill_pid(pid_server)
                kill_pid(pid_client)

        return stopTest

    def run_udp(self, bitrate, node='a', ect="nonect"):
        """
        Run UDP traffic at a constant bitrate

        ect: ect0 = ECT(0), ect1 = ECT(1), all other is Non-ECT

        Returns a lambda to stop the traffic
        """

        tos = ''
        if ect == 'ect1':
            tos = "--tos 0x01" # ECT(1)
        elif ect == 'ect0':
            tos="--tos 0x02" # ECT(0)
        else:
            ect = 'nonect'

        server_port = self.get_next_traffic_port()

        node = 'A' if node == 'a' else 'B'

        self.save_hint('traffic=udp node=%s%s client=%s rate=%d ect=%s' % (node, node, server_port, bitrate, ect))

        cmd_server = ssh['-tt', os.environ['IP_CLIENT%s_MGMT' % node], 'iperf -s -p %d' % server_port]

        # bitrate to iperf is the udp data bitrate, not the ethernet frame size as we want
        framesize = 1514
        headers = 42
        length = framesize - headers
        bitrate = bitrate * length / framesize

        cmd_client = ssh['-tt', os.environ['IP_SERVER%s_MGMT' % node], 'sleep 0.5; iperf -c %s -p %d %s -u -l %d -R -b %d -i 1 -t 99999' %
                          (os.environ['IP_CLIENT%s' % node], server_port, tos, length, bitrate)]

        if self.dry_run:
            if self.verbose > 0:
                print(get_shell_cmd(cmd_server))
                print(get_shell_cmd(cmd_client))

            def stopTest():
                pass

        else:
            pid_server = self.run(cmd_server, bg=True, verbose=True)
            pid_client = self.run(cmd_client, bg=True, verbose=True)

            add_known_pid(pid_server)
            add_known_pid(pid_client)

            def stopTest():
                kill_pid(pid_client)
                kill_pid(pid_server)

        return stopTest

    def run_speedometer(self, max_bitrate, delay=0.5):
        max_bitrate = max_bitrate / 8

        cmd = local['speedometer']['-s', '-i', '%f' % delay, '-l', '-t', os.environ['IFACE_CLIENTS'], '-m', '%d' % max_bitrate]

        if self.dry_run:
            if self.verbose > 0:
                print(get_shell_cmd(cmd))
        else:
            pid = self.run(cmd, verbose=self.verbose > 0)
            add_known_pid(pid)

    def run_ta(self, bg=False):
        net = re.sub(r'\.[0-9]+$', '.0', os.environ['IP_AQM_C'])

        pcapfilter = 'ip and dst net %s/24 and (tcp or udp)' % net
        ipclass = 'f'

        cmd = bash['-c', "echo 'Idling a bit before running ta...'; sleep %f; ../../traffic_analyzer/ta $IFACE_CLIENTS '%s' '%s' %d %s %d" %
                   (self.ta_idle, pcapfilter, self.get_testfolder(), self.ta_delay, ipclass, self.ta_samples)]

        if self.dry_run:
            pid = -1
            if self.verbose > 0:
                print(get_shell_cmd(cmd))
        else:
            pid = self.run(cmd, verbose=self.verbose > 0, bg=bg)

            # we add it to the kill list in case the script is terminated
            add_known_pid(pid)

        return pid

    def run_monitor_setup(self):
        cmd = local['watch']['-n', '.2', '../show_setup.sh', '-vir', '%s' % os.environ['IFACE_CLIENTS']]

        if self.dry_run:
            if self.verbose > 0:
                print(get_shell_cmd(cmd))
        else:
            pid = self.run(cmd, verbose=self.verbose > 0)
            add_known_pid(pid)

    def save_hint_set(self, text):
        if self.verbose > 1:
            print("hint(set): " + text)

        if not self.dry_run:
            TestEnv.save_hint_to_folder(self.set_folder, text)

    def save_hint(self, text):
        if self.verbose > 1:
            print("hint(test): " + text)

        if not self.dry_run:
            TestEnv.save_hint_to_folder(self.get_testfolder(), text)

    @staticmethod
    def save_hint_to_folder(folder, text):
        os.makedirs(folder, exist_ok=True)

        with open(folder + '/details', 'a') as f:
            f.write(text + '\n')

    @staticmethod
    def remove_hint(folder):
        file = folder + '/details'
        if os.path.isfile(file):
            os.remove(file)

    def get_testfolder(self):
        return self.set_folder + '/test-' + str(self.testtag if self.testtag is not None else self.get_testnum())

    def get_testnum(self):
        return '%03d' % self.testnum

    def analyze(self):
        Testbed.analyze_results(self.get_testfolder(), dry_run=self.dry_run)
        self.save_hint('data_analyzed')

    def check_folder(self, testfolder):
        if os.path.exists(testfolder):
            # don't skip if it is an incomplete test
            if not os.path.isfile(testfolder + '/details'):
                print('-----------------------------------------------------')
                print('Skipping existing and UNRECOGNIZED testcase directory')
                print('-----------------------------------------------------')
                print()
                self.skipped_last = True
                return False
            else:
                with open(testfolder + '/details') as f:
                    for line in f:
                        if line.strip() == 'data_collected':
                            print('------------------------------------')
                            print('Skipping testcase with existing data')
                            print('------------------------------------')
                            print()
                            self.skipped_last = True
                            self.data_collected = True
                            return False

                # clean up previous run
                print('-------------------------')
                print('Rerunning incomplete test')
                print('-------------------------')
                print()
                if not self.dry_run:
                    shutil.rmtree(testfolder)

        if not self.dry_run:
            os.makedirs(testfolder, exist_ok=True)

        return True

    def run_test(self, the_test, testbed, tag=None, xticlabel=None, xaxislabel=None):
        """Run a single test (the smallest possible test)

        the_test: Method that generates test data
        tag: String appended to test case directory name
        xticlabel: The x label value for this specific test when aggregated
        xaxislabel: Description of the xtic values
        """

        self.testnum += 1
        self.testtag = tag
        if tag is not None:
            if tag in self.tags_used:
                raise Exception("Tag must be unique inside a test set (tag: %s)" % tag)

            self.tags_used.append(tag)

        testfolder = self.get_testfolder()
        self.testfolders.append(testfolder)

        testcase = 'TESTCASE %s' % testfolder
        print()
        print()
        print('=' * len(testcase))
        print(testcase)
        print('=' * len(testcase))
        print(str(datetime.datetime.now()))
        print()

        if not self.check_folder(testfolder):
            return

        self.skipped_last = False
        start = time.time()

        testbed.reset(dry_run=self.dry_run, verbose=self.verbose)
        print('%.2f s: Testbed reset' % (time.time()-start))

        testbed.setup(dry_run=self.dry_run, verbose=self.verbose)

        print('%.2f s: Testbed initialized, starting test' % (time.time()-start))
        print()

        self.save_hint('type test')
        self.save_hint('xticlabel %s' % ('' if xticlabel is None else xticlabel))
        self.save_hint('xaxislabel %s' % ('' if xaxislabel is None else xaxislabel))
        self.save_hint('ta_idle %s' % self.ta_idle)
        self.save_hint('ta_delay %s' % self.ta_delay)
        self.save_hint('ta_samples %s' % self.ta_samples)

        hint = testbed.get_hint(dry_run=self.dry_run, verbose=self.verbose)
        if self.verbose > 1:
            print(hint)
        if not self.dry_run:
            with open(testfolder + '/details', 'a') as f:
                f.write(hint + "\n")

        pid_ta = self.run_ta(bg=not self.is_interactive)

        if self.is_interactive and not self.dry_run:
            self.run_monitor_setup()
            self.run_speedometer(testbed.bitrate * 1.1, delay=0.05)

        the_test(self, testbed)

        if not self.dry_run:
            waitpid(pid_ta)  # wait until 'ta' quits

        kill_known_pids()

        print()
        print('%.2f s: Data collection finished' % (time.time()-start))
        self.save_hint('data_collected')
        if not self.dry_run:
            self.data_collected = True

        self.get_terminal().cleanup()


class TestCollection():
    """Organizes test sets in collections and stores metadata used to automatically plot

    Test hierarchy looks like (from bottom up):
    - single tests
    - sets of single tests
    - collection of sets
    - collection of collections, and so on
    """

    def __init__(self, folder, title=None, subtitle=None, parent=None):
        self.title = title
        if parent:
            self.folder = parent.folder + '/' + folder
        else:
            self.folder = folder
        self.parent = parent
        self.parent_called = False

        TestEnv.remove_hint(self.folder)
        TestEnv.save_hint_to_folder(self.folder, 'type collection')

        if title is not None:
            TestEnv.save_hint_to_folder(self.folder, 'title %s' % title)

        if subtitle is not None:
            TestEnv.save_hint_to_folder(self.folder, 'subtitle %s' % subtitle)

    def add_set(self, set_folder):
        TestEnv.save_hint_to_folder(self.folder, 'sub %s' % os.path.basename(set_folder))

        if self.parent and not self.parent_called:
            self.parent_called = True
            self.parent.add_collection(self)

    def add_collection(self, collection):
        TestEnv.save_hint_to_folder(self.folder, 'sub %s' % os.path.basename(collection.folder))

        if self.parent and not self.parent_called:
            self.parent_called = True
            self.parent.add_collection(self)

    def run_set(self, testobj, my_set, testbed, foldername, **kwargs):
        set_folder = self.folder + '/' + foldername
        self.add_set(set_folder)
        testobj.run_set(my_set, testbed, set_folder, **kwargs)




class TestbedTesting():
    def testbed(self):
        testbed = Testbed()
        testbed.bitrate = 10*1000*1000
        testbed.aqm_pi2()
        testbed.rtt_servera = 25
        testbed.rtt_serverb = 25
        testbed.cc_b = 'dctcp'
        testbed.ecn_b = 1
        return testbed

    def run_set(self, method_set, testbed, set_folder, plot_only=False, title=None, subtitle=None):
        testenv = TestEnv(set_folder)

        # overload run_test so we can hook into it
        testenv.run_test_orig = testenv.run_test
        testenv.run_test = functools.partial(types.MethodType(TestbedTesting.run_test_overload, testenv), plot_only)

        if plot_only:
            testenv.dry_run = True

        if not testenv.dry_run:
            TestEnv.remove_hint(testenv.set_folder)

        testenv.save_hint_set('type set')

        if title is not None:
            testenv.save_hint_set('title %s' % title)

        if subtitle is not None:
            testenv.save_hint_set('subtitle %s' % subtitle)

        method_set(testenv, testbed)

        if plot_only:
            self.generate_set_plots(testenv)

        return testenv

    # this method is overloaded to TestEnv, so the context will be a TestEnv object when run
    def run_test_overload(self, plot_only, the_test, testbed, **kwargs):
        self.run_test_orig(the_test, testbed, **kwargs)


        if not self.skipped_last and not self.dry_run:
            self.analyze()

            # plot this single flow
            p = Plot()
            p.plot_flow(self.get_testfolder())

        self.save_hint_set('sub %s' % os.path.basename(self.get_testfolder()))

    def generate_set_plots(self, testenv):
        p = Plot()
        p.plot_multiple_flows(testenv.testfolders, testenv.set_folder + '/analysis_merged')


class OverloadTesting(TestbedTesting):
    def test_testbed(self):
        testbed = self.testbed()
        testbed.rtt_servera = testbed.rtt_serverb = 100
        testbed.cc_b = 'dctcp'
        testbed.ecn_b = 1
        testbed.aqm_pi2()

        testbed.reset()
        testbed.setup()
        testbed.print_setup()

    def test_cubic(self):
        testbed = self.testbed()

        test_collection1 = TestCollection('testsets/cubic', title='Testing cubic vs other congestion controls',
                                          subtitle='Linkrate: 10 Mbit')

        for aqm, foldername, aqmtitle in [#(testbed.aqm_pi2, 'pi2', 'AQM: pi2'),
                                          (functools.partial(testbed.aqm_pi2, params='l_thresh 50000'), 'pi2-l_thresh-50000', 'AQM: pi2 (l\_thresh = 50000)'),
                                          #(testbed.aqm_fq_codel, 'fq_codel', 'AQM: fq_codel'),
                                          #(testbed.aqm_red, 'red', 'AQM: RED'),
                                          #(testbed.aqm_default, 'no-aqm', 'No AQM'),
                                          ]:

            aqm()
            test_collection2 = TestCollection(foldername, title=aqmtitle, parent=test_collection1)

            #for numflows in [1,2,3]:
            for numflows in [1]:
                test_collection3 = TestCollection('flows-%d' % numflows, title='%d flows each' % numflows, parent=test_collection2)

                for cc, ecn, foldername, title in [#('cubic', 2, 'cubic',    'cubic vs cubic'),
                                                   ('cubic', 1, 'cubic-ecn','cubic vs cubic-ecn'),
                                                   ('dctcp', 1, 'dctcp',    'cubic vs dctcp')]:
                    testbed.cc_b = cc
                    testbed.ecn_b = ecn

                    def my_set(testenv, testbed):
                        #for rtt in [2, 5, 10, 25, 50, 75, 100, 125, 150, 175, 200, 250, 300, 400]:
                        for rtt in [5, 10, 25, 50, 100, 200]:
                            testbed.rtt_servera = rtt
                            testbed.rtt_serverb = rtt
                            testenv.ta_idle = (rtt / 1000) * 20 + 4

                            def my_test(testenv, testbed):
                                for i in range(numflows):
                                    testenv.run_greedy(node='a')
                                    testenv.run_greedy(node='b')

                            testenv.run_test(my_test, testbed, tag=rtt, xticlabel=rtt, xaxislabel='RTT')

                    test_collection3.run_set(self, my_set, testbed, foldername=foldername, title=title, plot_only=True)

    def test_increasing_udp_traffic(self):
        """Test UDP-traffic in both queues with increasing bandwidth"""
        testbed = self.testbed()

        def my_set(testenv, testbed):
            def my_test(testenv, testbed):
                for x in range(10):
                    testenv.run_udp(node='a', bitrate=1250000, ect='nonect')
                    testenv.run_udp(node='b', bitrate=1250000, ect='ect0')
                    time.sleep(2)

            testenv.run_test(my_test, testbed, xticlabel='test 1')
            testenv.run_test(my_test, testbed, xticlabel='test 2')
            testenv.run_test(my_test, testbed, xticlabel='test 3')
            testenv.run_test(my_test, testbed, xticlabel='test 4')

        self.run_set(my_set, testbed, 'testsets/increasing-udp', title='Testing increasing UDP-rate in same test',
                     subtitle='Look at graphs for the individual tests for this to have any use')
        plot_folder_compare('testsets/increasing-udp')

    def test_speeds(self):
        """Test one UDP-flow vs one TCP-greedy flow with different UDP speeds and UDP ECT-flags"""
        testbed = self.testbed()

        test_collection = TestCollection('testsets/speeds', title='Overload with UDP')

        for ect, title in [('nonect', 'UDP with Non-ECT'),
                           ('ect1', 'UDP with ECT(1)')]:
            def my_set(testenv, testbed):
                testenv.ta_samples = 250
                testenv.ta_delay = 500
                testenv.ta_idle = 5

                speeds = [5000, 9000, 9500, 10000, 10500, 11000, 12000, 12500,
                          13000, 13100, 13200, 13400, 13500, 14000, 28000, 50000, 500000]

                for speed in speeds:
                    def my_test(testenv, testbed):
                        testenv.run_greedy(node='b')
                        testenv.run_udp(node='a', bitrate=speed*1000, ect=ect)

                    testenv.run_test(my_test, testbed, tag=speed, xticlabel=speed, xaxislabel='UDP bitrate [kb/s]')

            test_collection.run_set(self, my_set, testbed, foldername=ect, title=title)

    def test_tcp_competing(self):
        testbed = self.testbed()
        testbed.aqm_pi2()
        testbed.cc_a = 'cubic'
        testbed.ecn_a = 1
        testbed.cc_b = 'cubic'
        testbed.ecn_b = 2

        def my_set(testenv, testbed):
            def my_test(testenv, testbed):
                testenv.run_greedy(node='a')
                testenv.run_greedy(node='b')

            testenv.run_test(my_test, testbed)

        self.run_set(my_set, testbed, 'testsets/tcp-competing')

    def test_plot_test_data(self):
        testbed = self.testbed()
        testbed.aqm_pi2()

        test_collection = TestCollection('testsets/plot-testdata', title='Testing cubic vs different flows')

        for name, n_a, n_b, title in [('traffic-ab', 1, 1, 'traffic both machines'),
                                     ('traffic-a',  1, 0, 'traffic only a'),
                                     ('traffic-b',  0, 1, 'traffic only b')]:
            def my_set(testenv, testbed):
                testenv.ta_samples = 5
                testenv.ta_idle = .5
                testenv.ta_delay = 500

                def my_test(testenv, testbed):
                    for n in range(n_a):
                        testenv.run_greedy(node='a')
                    for n in range(n_b):
                        testenv.run_greedy(node='b')

                for rtt in [2, 5, 8, 10, 20, 50, 100]:
                    testbed.rtt_servera = testbed.rtt_serverb = rtt

                    for i in range(1,6):
                        testenv.run_test(my_test, testbed, tag='rtt-%s-%d' % (rtt, i), xticlabel=rtt, xaxislabel='RTT')

            test_collection.run_set(self, my_set, testbed, name, title=title, plot_only=True)


if __name__ == '__main__':

    if True:
        t = OverloadTesting()
        t.test_plot_test_data()
        #t.test_testbed()
        #t.test_cubic()
        #t.test_increasing_udp_traffic()
