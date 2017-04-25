"""
This module contains the testbed logic
"""

import math
import os
from plumbum import local, FG
from plumbum.cmd import bash
from plumbum.commands.processes import ProcessExecutionError

from . import logger
from .terminal import get_log_cmd


def get_testbed_script_path():
    return "aqmt-testbed.sh"


def require_on_aqm_node():
    testbed_script = get_testbed_script_path()
    bash['-c', 'set -e; source %s; require_on_aqm_node' % testbed_script] & FG


class Testbed:
    """
    A object representing the desired testbed configuration and utilities
    to apply the configuration. This object is used throughout tests
    and is mutated and reapplied before tests to change the setup.
    """
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

        self.aqm_name = 'pfifo_aqmt'  # we need a default aqm to get queue delay
        self.aqm_params = ''

        self.cc_a = 'cubic'
        self.ecn_a = self.ECN_ALLOW
        self.cc_b = 'cubic'
        self.ecn_b = self.ECN_ALLOW

        self.ta_idle = None  # time to skip in seconds when building aggregated data, default to be RTT-dependent
        self.ta_delay = 1000
        self.ta_samples = 250

        self.traffic_port = 5500

    def aqm(self, name='', params=''):
        if name == 'pfifo':
            name = 'pfifo_aqmt'  # use our custom version with aqmt

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

    def rtt(self, rtt_servera, rtt_serverb=None, rtt_clients=0):
        if rtt_serverb is None:
            rtt_serverb = rtt_servera

        self.rtt_clients = rtt_clients  # in ms
        self.rtt_servera = rtt_servera  # in ms
        self.rtt_serverb = rtt_serverb  # in ms

    def get_ta_samples_to_skip(self):
        time = self.ta_idle
        if time is None:
            time = (max(self.rtt_clients, self.rtt_servera, self.rtt_serverb) / 1000) * 40 + 4

        samples = time * 1000 / self.ta_delay
        return math.ceil(samples)

    def setup(self, dry_run=False, log_level=logger.DEBUG):
        cmd = bash['-c', """
            # configuring testbed
            set -e
            source """ + get_testbed_script_path() + """

            set_offloading off

            configure_clients_edge """ + '%s %s %s "%s" "%s"' % (self.bitrate, self.rtt_clients, self.aqm_name, self.aqm_params, self.netem_clients_params) + """
            configure_server_edge $IP_SERVERA_MGMT $IP_AQM_SA $IFACE_SERVERA $IFACE_ON_SERVERA """ + '%s "%s"' % (self.rtt_servera, self.netem_servera_params) + """
            configure_server_edge $IP_SERVERB_MGMT $IP_AQM_SB $IFACE_SERVERB $IFACE_ON_SERVERB """ + '%s "%s"' % (self.rtt_serverb, self.netem_serverb_params) + """

            configure_host_cc $IP_CLIENTA_MGMT """ + '%s %s' % (self.cc_a, self.ecn_a) + """
            configure_host_cc $IP_SERVERA_MGMT """ + '%s %s' % (self.cc_a, self.ecn_a) + """
            configure_host_cc $IP_CLIENTB_MGMT """ + '%s %s' % (self.cc_b, self.ecn_b) + """
            configure_host_cc $IP_SERVERB_MGMT """ + '%s %s' % (self.cc_b, self.ecn_b) + """
            """]

        logger.log(log_level, get_log_cmd(cmd))
        if not dry_run:
            try:
                cmd & FG
            except ProcessExecutionError:
                return False

        return True

    @staticmethod
    def reset(dry_run=False, log_level=logger.DEBUG):
        cmd = bash['-c', """
            # resetting testbed
            set -e
            source """ + get_testbed_script_path() + """

            kill_all_traffic
            reset_aqm_client_edge
            reset_aqm_server_edge
            reset_all_hosts_edge
            reset_all_hosts_cc
            """]

        logger.log(log_level, get_log_cmd(cmd))
        if not dry_run:
            try:
                cmd & FG
            except ProcessExecutionError:
                return False

        return True

    def get_next_traffic_port(self, node_to_check=None):
        while True:
            tmp = self.traffic_port
            self.traffic_port += 1

            if node_to_check is not None:
                if 'CLIENT' not in node_to_check and 'SERVER' not in node_to_check:
                    raise Exception('Expecting node name like CLIENTA. Got: %s' % node_to_check)
                host = '$IP_%s_MGMT' % node_to_check
                import time
                start = time.time()
                res = bash['-c', """
                    set -e
                    source """ + get_testbed_script_path() + """
                    check_port_in_use """ + host + """ """ + str(tmp) + """ 2>/dev/null
                    """]()
                if int(res) > 0:
                    # port in use, try next
                    logger.warn('Port %d on node %s was in use - will try next port' % (tmp, node_to_check))
                    continue

            break

        return tmp

    @staticmethod
    def get_aqm_options(name):
        testbed_script = get_testbed_script_path()
        res = bash['-c', 'set -e; source %s; get_aqm_options %s' % (testbed_script, name)]()
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
            testbed_script = get_testbed_script_path()
            out += (bash['-c', 'set -e; source %s; get_host_cc "$%s"' % (testbed_script, ip)] | local['tr']['\n', ' '])().strip()
            out += '\n'

        return out.strip()

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
