#!/usr/bin/env python3

"""Henrik's test framework

For interactive tests (with live plots), run:
$ TEST_INTERACTIVE=1 ./mytest.py

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
from .plot import Plot, plot_folder_compare, plot_folder_flows

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

    def run_fg(self, cmd, verbose=False):
        cmd = get_shell_cmd(cmd)
        if verbose:
            print(cmd)

        pane_pid = tmux['split-window', '-dP', '-t', self.get_pane_id(self.win_id), '-F', '#{pane_pid}', cmd]().strip()

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
            res = tmux['new-window', '-adP', '-F', '#{window_id} #{pane_pid}', '-t', self.win_id, cmd]().strip().split()
            self.win_bg_id = res[0]
            pane_pid = res[1]
            tmux['set-window-option', '-t', self.win_bg_id, 'remain-on-exit', 'on'] & FG

        else:
            pane_pid = tmux['split-window', '-dP', '-t', self.get_pane_id(self.win_bg_id), '-F', '#{pane_pid}', cmd]().strip()
            tmux['select-layout', '-t', self.win_bg_id, 'tiled'] & FG

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

    def aqm_pie(self, params=None):
        self.aqm_name = 'pie'
        self.aqm_params = 'ecn' if params is None else params

    def aqm_fq_codel(self):
        self.aqm_name = 'fq_codel'
        self.aqm_params = 'ecn'

    def aqm_pfifo(self):
        self.aqm_name = 'pfifo_qsize'
        self.aqm_params = ''

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

    def setup(self, dry_run=False, verbose=0):
        cmd = bash['-c', """
            set -e
            source """ + get_common_script_path() + """

            configure_clients_edge """ + '%s %s %s "%s" "%s"' % (self.bitrate, self.rtt_clients, self.aqm_name, self.aqm_params, self.netem_clients_params) + """
            configure_server_edge $IP_SERVERA_MGMT $IP_AQM_SA $IFACE_SERVERA $IFACE_ON_SERVERA """ + '%s "%s"' % (self.rtt_servera, self.netem_servera_params) + """
            configure_server_edge $IP_SERVERB_MGMT $IP_AQM_SB $IFACE_SERVERB $IFACE_ON_SERVERB """ + '%s "%s"' % (self.rtt_serverb, self.netem_serverb_params) + """

            configure_host_cc $IP_CLIENTA_MGMT """ + '%s %s' % (self.cc_a, self.ecn_a) + """
            configure_host_cc $IP_SERVERA_MGMT """ + '%s %s' % (self.cc_a, self.ecn_a) + """
            configure_host_cc $IP_CLIENTB_MGMT """ + '%s %s' % (self.cc_b, self.ecn_b) + """
            configure_host_cc $IP_SERVERB_MGMT """ + '%s %s' % (self.cc_b, self.ecn_b) + """
            """]

        if dry_run:
            if verbose > 1:
                print(get_shell_cmd(cmd))
        else:
            try:
                cmd & FG
            except ProcessExecutionError:
                return False

        return True

    def reset(self, dry_run=False, verbose=0):
        cmd = bash['-c', """
            set -e
            source """ + get_common_script_path() + """
            kill_all_traffic
            reset_aqm_client_edge
            reset_aqm_server_edge
            reset_all_hosts_edge
            reset_all_hosts_cc
            """]

        if dry_run:
            if verbose > 1:
                print(get_shell_cmd(cmd))
        else:
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
            common = get_common_script_path()
            res = (bash['-c', 'set -e; source %s; get_host_cc "$%s"' % (common, ip)] | local['tr']['\n', ' '])().strip()
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

        if not os.path.exists(testfolder + '/derived'):
            os.makedirs(testfolder + '/derived')

        cmd = local['../traffic_analyzer/calc_henrste'][testfolder, fairness, str(nbrf), str(bitrate), str(rtt_l4s), str(rtt_classic), str(nbr_l4s_flows), str(nbr_classic_flows)]
        if verbose > 0:
            print(get_shell_cmd(cmd))

        if dry_run:
            if verbose > 0:
                print("Skipping post processing due to dry run")

        else:
            cmd()

            start = time.time()

            qd = QueueDelay()
            qd.processTest(testfolder)

            tr = TaggedRate()
            tr.processTest(testfolder)

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


class TestCase():
    def __init__(self, testenv, folder, tag=None, title=None, titlelabel=None):
        self.testenv = testenv
        self.test_folder = folder
        self.tag = tag

        self.title = title
        self.titlelabel = titlelabel

        self.directory_error = False
        self.data_collected = False
        self.already_exists = False

        self.check_folder()

    def run_tcp_netcat(self, node='a', tag=None):
        """
        Run TCP traffic with netcat (nc)
        """
        server_port = self.testenv.testbed.get_next_traffic_port()

        node = 'A' if node == 'a' else 'B'

        self.save_hint('traffic=tcp type=netcat node=%s%s server=%d tag=%s' % (node, node, server_port, 'No-tag' if tag is None else tag))

        cmd1 = ssh['-tt', os.environ['IP_SERVER%s_MGMT' % node], 'cat /dev/zero | nc -l %d >/dev/null' % server_port]
        cmd2 = ssh['-tt', os.environ['IP_CLIENT%s_MGMT' % node], 'sleep 0.2; nc -d %s %d >/dev/null' % (os.environ['IP_SERVER%s' % node], server_port)]

        if self.testenv.dry_run:
            if self.testenv.verbose > 0:
                print(get_shell_cmd(cmd1))
                print(get_shell_cmd(cmd2))

            def stopTest():
                pass

        else:
            pid1 = self.testenv.run(cmd1, bg=True, verbose=True)
            pid2 = self.testenv.run(cmd2, bg=True, verbose=True)
            add_known_pid(pid1)
            add_known_pid(pid2)

            def stopTest():
                kill_pid(pid1)
                kill_pid(pid2)

        return stopTest

    def run_tcp_iperf(self, node='a', tag=None):
        """
        Run TCP traffic with iperf2
        """
        server_port = self.testenv.testbed.get_next_traffic_port()

        node = 'A' if node == 'a' else 'B'

        self.save_hint('traffic=tcp type=iperf2 node=%s%s client=%d tag=%s' % (node, node, server_port, 'No-tag' if tag is None else tag))

        cmd1 = ssh['-tt', os.environ['IP_CLIENT%s_MGMT' % node], 'iperf -s -p %d' % server_port]
        cmd2 = ssh['-tt', os.environ['IP_SERVER%s_MGMT' % node], 'sleep 0.2; iperf -c %s -p %d -t 86400' % (os.environ['IP_CLIENT%s' % node], server_port)]

        if self.testenv.dry_run:
            if self.testenv.verbose > 0:
                print(get_shell_cmd(cmd1))
                print(get_shell_cmd(cmd2))

            def stopTest():
                pass

        else:
            pid1 = self.testenv.run(cmd1, bg=True, verbose=True)
            pid2 = self.testenv.run(cmd2, bg=True, verbose=True)
            add_known_pid(pid1)
            add_known_pid(pid2)

            def stopTest():
                kill_pid(pid1)
                kill_pid(pid2)

        return stopTest

    def run_scp(self, node='a', tag=None):
        """
        Run TCP traffic with SCP (SFTP)

        Note there are some issues with the window size inside
        SSH as it uses its own sliding window. This test is therefore
        not reliable with a high BDP

        See:
        - http://www.slideshare.net/datacenters/enabling-high-performance-bulk-data-transfers-with-ssh
        - http://stackoverflow.com/questions/8849240/why-when-i-transfer-a-file-through-sftp-it-takes-longer-than-ftp

        All traffic goes over port 22 as of now. Tagging is
        not really possible because of this.
        """
        server_port = -1

        node = 'A' if node == 'a' else 'B'

        self.save_hint('traffic=tcp type=scp node=%s%s server=%s tag=%s' % (node, node, server_port, 'No-tag' if tag is None else tag))

        cmd = ssh['-tt', os.environ['IP_SERVER%s_MGMT' % node], 'scp /opt/testbed/bigfile %s:/tmp/' % (os.environ['IP_CLIENT%s' % node])]

        if self.testenv.dry_run:
            if self.testenv.verbose > 0:
                print(get_shell_cmd(cmd))

            def stopTest():
                pass

        else:
            pid_server = self.testenv.run(cmd, bg=True, verbose=True)
            add_known_pid(pid_server)

            def stopTest():
                kill_pid(pid_server)

        return stopTest

    def run_greedy(self, node='a', tag=None):
        """
        Run greedy TCP traffic

        Greedy = always data to send, full frames

        node: a or b (a is normally classic traffic, b is normally l4s)

        Tagging makes it possible to map similar traffic from multiple tests,
        despite being different ports and setup

        Returns a lambda to stop the traffic
        """
        server_port = self.testenv.testbed.get_next_traffic_port()

        node = 'A' if node == 'a' else 'B'

        self.save_hint('traffic=tcp type=greedy node=%s%s server=%s tag=%s' % (node, node, server_port, 'No-tag' if tag is None else tag))

        cmd1 = ssh['-tt', os.environ['IP_SERVER%s_MGMT' % node], '/opt/testbed/greedy_generator/greedy -vv -s %d' % server_port]
        cmd2 = ssh['-tt', os.environ['IP_CLIENT%s_MGMT' % node], 'sleep 0.2; /opt/testbed/greedy_generator/greedy -vv %s %d' % (os.environ['IP_SERVER%s' % node], server_port)]

        if self.testenv.dry_run:
            if self.testenv.verbose > 0:
                print(get_shell_cmd(cmd1))
                print(get_shell_cmd(cmd2))

            def stopTest():
                pass

        else:
            pid_server = self.testenv.run(cmd1, bg=True, verbose=True)
            pid_client = self.testenv.run(cmd2, bg=True, verbose=True)
            add_known_pid(pid_server)
            add_known_pid(pid_client)

            def stopTest():
                kill_pid(pid_server)
                kill_pid(pid_client)

        return stopTest

    def run_udp(self, bitrate, node='a', ect="nonect", tag=None):
        """
        Run UDP traffic at a constant bitrate

        ect: ect0 = ECT(0), ect1 = ECT(1), all other is Non-ECT

        Tagging makes it possible to map similar traffic from multiple tests,
        despite being different ports and setup

        Returns a lambda to stop the traffic
        """

        tos = ''
        if ect == 'ect1':
            tos = "--tos 0x01" # ECT(1)
        elif ect == 'ect0':
            tos="--tos 0x02" # ECT(0)
        else:
            ect = 'nonect'

        server_port = self.testenv.testbed.get_next_traffic_port()

        node = 'A' if node == 'a' else 'B'

        self.save_hint('traffic=udp node=%s%s client=%s rate=%d ect=%s tag=%s' % (node, node, server_port, bitrate, ect, 'No-tag' if tag is None else tag))

        cmd_server = ssh['-tt', os.environ['IP_CLIENT%s_MGMT' % node], 'iperf -s -p %d' % server_port]

        # bitrate to iperf is the udp data bitrate, not the ethernet frame size as we want
        framesize = 1514
        headers = 42
        length = framesize - headers
        bitrate = bitrate * length / framesize

        cmd_client = ssh['-tt', os.environ['IP_SERVER%s_MGMT' % node], 'sleep 0.5; iperf -c %s -p %d %s -u -l %d -R -b %d -i 1 -t 99999' %
                          (os.environ['IP_CLIENT%s' % node], server_port, tos, length, bitrate)]

        if self.testenv.dry_run:
            if self.testenv.verbose > 0:
                print(get_shell_cmd(cmd_server))
                print(get_shell_cmd(cmd_client))

            def stopTest():
                pass

        else:
            pid_server = self.testenv.run(cmd_server, bg=True, verbose=True)
            pid_client = self.testenv.run(cmd_client, bg=True, verbose=True)

            add_known_pid(pid_server)
            add_known_pid(pid_client)

            def stopTest():
                kill_pid(pid_client)
                kill_pid(pid_server)

        return stopTest

    def save_hint(self, text):
        if self.testenv.verbose > 1:
            print("hint(test): " + text)

        if not self.testenv.dry_run:
            TestEnv.save_hint_to_folder(self.test_folder, text)

    def print_header(self, h1, h2):
        print()
        print('=' * len(h1) + ((' ' + '-' * len(h2)) if h2 is not None else ''))
        print(h1 + ((' ' + h2) if h2 is not None else ''))
        print('=' * len(h1) + ((' ' + '-' * len(h2)) if h2 is not None else ''))
        print(str(datetime.datetime.now()))
        print()

    def check_folder(self):
        h1 = 'TESTCASE %s' % self.test_folder
        h2 = None

        if os.path.exists(self.test_folder):
            if not os.path.isfile(self.test_folder + '/details'):
                self.print_header(h1, 'Skipping existing and UNRECOGNIZED testcase directory')
                self.directory_error = True
                return
            else:
                if not self.testenv.retest:
                    with open(self.test_folder + '/details') as f:
                        for line in f:
                            if line.strip() == 'data_collected':
                                self.print_header(h1, 'Skipping testcase with existing data')
                                self.already_exists = True
                                return

                    # clean up previous run
                    h2 = 'Rerunning incomplete test'
                else:
                    h2 = 'Repeating existing test'

                if not self.testenv.dry_run:
                    shutil.rmtree(self.test_folder)

        self.print_header(h1, h2)

        if not self.testenv.dry_run:
            os.makedirs(self.test_folder, exist_ok=True)

    def run_ta(self, bg=False):
        net_c = re.sub(r'\.[0-9]+$', '.0', os.environ['IP_AQM_C'])
        net_sa = re.sub(r'\.[0-9]+$', '.0', os.environ['IP_AQM_SA'])
        net_sb = re.sub(r'\.[0-9]+$', '.0', os.environ['IP_AQM_SB'])

        pcapfilter = 'ip and dst net %s/24 and (src net %s/24 or src net %s/24) and (tcp or udp)' % (net_c, net_sa, net_sb)
        ipclass = 'f'

        cmd = bash['-c', "set -e; echo 'Idling a bit before running ta...'; sleep %f; . vars.sh; mkdir -p '%s'; sudo ../traffic_analyzer/ta $IFACE_CLIENTS '%s' '%s/ta' %d %s %d" %
                   (self.testenv.testbed.get_ta_idle(), self.test_folder, pcapfilter, self.test_folder,
                    self.testenv.testbed.ta_delay, ipclass, self.testenv.testbed.ta_samples)]

        if self.testenv.dry_run:
            pid = -1
            if self.testenv.verbose > 0:
                print(get_shell_cmd(cmd))
        else:
            pid = self.testenv.run(cmd, verbose=self.testenv.verbose > 0, bg=bg)

            # we add it to the kill list in case the script is terminated
            add_known_pid(pid)

        return pid

    def calc_post_wait_time(self):
        """The time it will idle after the test is run"""
        return max(self.testenv.testbed.rtt_clients, self.testenv.testbed.rtt_servera, self.testenv.testbed.rtt_serverb) / 1000 * 5 + 2

    def calc_estimated_run_time(self):
        return self.testenv.testbed.ta_samples * self.testenv.testbed.ta_delay / 1000 + self.testenv.testbed.get_ta_idle() + self.calc_post_wait_time()

    def run(self, test_fn):
        if self.directory_error:
            raise Exception('Cannot run a test with an unrecognized directory')
        if self.data_collected:
            raise Exception('Cannot run the same TestCase multiple times')

        start = time.time()

        if not self.testenv.testbed.reset(dry_run=self.testenv.dry_run, verbose=self.testenv.verbose):
            raise Exception('Reset failed')
        print('%.2f s: Testbed reset' % (time.time()-start))

        if not self.testenv.testbed.setup(dry_run=self.testenv.dry_run, verbose=self.testenv.verbose):
            raise Exception('Setup failed')
        if not self.testenv.dry_run:
            self.testenv.testbed.print_setup()

        print()
        print('%.2f s: Testbed initialized, starting test. Estimated time to finish: %d s' % (time.time()-start, self.calc_estimated_run_time()))
        print()

        self.save_hint('type test')
        self.save_hint('title %s' % ('' if self.title is None else self.title))
        self.save_hint('titlelabel %s' % ('' if self.titlelabel is None else self.titlelabel))
        self.save_hint('ta_idle %s' % self.testenv.testbed.get_ta_idle())
        self.save_hint('ta_delay %s' % self.testenv.testbed.ta_delay)
        self.save_hint('ta_samples %s' % self.testenv.testbed.ta_samples)

        hint = self.testenv.testbed.get_hint(dry_run=self.testenv.dry_run, verbose=self.testenv.verbose)
        if self.testenv.verbose > 1:
            print(hint)
        if not self.testenv.dry_run:
            with open(self.test_folder + '/details', 'a') as f:
                f.write(hint + "\n")

        pid_ta = self.run_ta(bg=not self.testenv.is_interactive)

        if self.testenv.is_interactive and not self.testenv.dry_run:
            self.testenv.run_monitor_setup()
            self.testenv.run_speedometer(self.testenv.testbed.bitrate * 1.1, delay=0.05)

        test_fn(self)

        if not self.testenv.dry_run:
            waitpid(pid_ta)  # wait until 'ta' quits

        kill_known_pids()

        print()
        print('%.2f s: Data collection finished' % (time.time()-start))
        self.save_hint('data_collected')
        self.data_collected = True

        if not self.testenv.testbed.reset(dry_run=self.testenv.dry_run, verbose=self.testenv.verbose):
            raise Exception('Reset failed')
        print('%.2f s: Testbed reset, waiting %.2f s for cooldown period' % (time.time()-start, self.calc_post_wait_time()))

        # in case there is a a queue buildup it should now free because the
        # testbed is reset (so no added RTT or rate limit) and we give it some
        # time to complete
        time.sleep(self.calc_post_wait_time())
        print('%.2f s: Finished waiting to let the connections finish' % (time.time()-start))

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
    def __init__(self, testbed, is_interactive=None, dry_run=False, verbose=1, reanalyze=False, replot=False, retest=False):
        self.testbed = testbed

        self.tests = []  # list of tests that has been run
        self.terminal = None

        if is_interactive is None:
            is_interactive = 'TEST_INTERACTIVE' in os.environ and os.environ['TEST_INTERACTIVE']  # run in tmux or not
        self.is_interactive = is_interactive
        self.dry_run = dry_run
        self.verbose = verbose
        self.reanalyze = reanalyze
        self.replot = replot
        self.retest = retest

        def exit_gracefully(signum, frame):
            kill_known_pids()
            self.get_terminal().cleanup()
            sys.exit()

        signal.signal(signal.SIGINT, exit_gracefully)
        signal.signal(signal.SIGTERM, exit_gracefully)

    def get_terminal(self):
        if self.terminal == None:
            self.terminal = Tmux() if self.is_interactive else Terminal()
        return self.terminal

    def run(self, cmd, bg=False, verbose=False):
        if bg:
            return self.get_terminal().run_bg(cmd, verbose=verbose)
        else:
            return self.get_terminal().run_fg(cmd, verbose=verbose)

    def run_speedometer(self, max_bitrate, delay=0.5):
        max_bitrate = max_bitrate / 8

        cmd = local['speedometer']['-s', '-i', '%f' % delay, '-l', '-t', os.environ['IFACE_CLIENTS'], '-m', '%d' % max_bitrate]

        if self.dry_run:
            if self.verbose > 0:
                print(get_shell_cmd(cmd))
        else:
            pid = self.run(cmd, verbose=self.verbose > 0)
            add_known_pid(pid)

    def run_monitor_setup(self):
        cmd = local['watch']['-n', '.2', './views/show_setup.sh', '-vir', '%s' % os.environ['IFACE_CLIENTS']]

        if self.dry_run:
            if self.verbose > 0:
                print(get_shell_cmd(cmd))
        else:
            pid = self.run(cmd, verbose=self.verbose > 0)
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
    - single tests
    - collection of tests
    - collection of collections, and so on
    """

    def __init__(self, folder, testenv=None, title=None, subtitle=None, parent=None):
        self.title = title

        if parent:
            self.folder = parent.folder + '/' + folder
            parent.add_collection(self)
            if testenv is None:
                testenv = parent.testenv
        else:
            self.folder = folder
            if testenv is None:
                raise Exception('Missing testenv object')

        self.testenv = testenv
        self.tags_used = []
        self.tests = []
        self.have_sub = False
        self.parent = parent
        self.parent_called = False

        TestEnv.remove_hint(self.folder)
        TestEnv.save_hint_to_folder(self.folder, 'type collection')

        if title is not None:
            TestEnv.save_hint_to_folder(self.folder, 'title %s' % title)

        if subtitle is not None:
            TestEnv.save_hint_to_folder(self.folder, 'subtitle %s' % subtitle)

    def check_and_add_tag(self, tag):
        if tag in self.tags_used:
            raise Exception("Tag must be unique inside same collection/test (tag: %s)" % tag)

        self.tags_used.append(tag)

    def add_collection(self, collection):
        self.check_and_add_tag(collection.folder)

    def add_sub(self, folder):
        self.have_sub = True
        TestEnv.save_hint_to_folder(self.folder, 'sub %s' % os.path.basename(folder))

        if self.parent and not self.parent_called:
            self.parent_called = True
            self.parent.add_sub(self.folder)

    def run_test(self, test_fn, tag, title=None, titlelabel=None):
        """Run a single test (the smallest possible test)

        test_fn: Method that generates test data
        tag: String appended to test case directory name
        title: The x label value for this specific test when aggregated
        titlelabel: Description of the title values
        """

        self.check_and_add_tag(tag)
        test = TestCase(testenv=self.testenv, folder=self.folder + '/test-' + str(tag),
                        title=title, titlelabel=titlelabel)

        self.tests.append(test)
        if not test.should_skip():
            test.run(test_fn)

        if (test.data_collected or test.already_exists) and not self.testenv.dry_run:
            if self.testenv.reanalyze or not test.already_exists:
                start = time.time()
                test.analyze()
                print('Analyzed test (%.2f s)' % (time.time()-start))

            if self.testenv.reanalyze or self.testenv.replot or not test.already_exists:
                start = time.time()
                test.plot()
                print('Plotted test (%.2f s)' % (time.time()-start))

            self.add_sub(test.test_folder)

        elif test.already_exists:
            self.add_sub(test.test_folder)

    def plot(self, swap_levels=[], **kwargs):
        print('Plotting multiple flows..')
        self.plot_tests_merged()
        self.plot_tests_compare(swap_levels=swap_levels, **kwargs)

    def plot_tests_merged(self):
        testfolders = []
        for test in self.tests:
            if test.has_valid_data():
                testfolders.append(test.test_folder)

        if len(testfolders) > 0:
            p = Plot()
            p.plot_multiple_flows(testfolders, self.folder + '/analysis_merged')

    def plot_tests_compare(self, swap_levels=[], **kwargs):
        if self.have_sub:
            plot_folder_compare(self.folder, swap_levels=swap_levels, **kwargs)


if __name__ == '__main__':
    print("This script is not to be run directly but used by other tests")
