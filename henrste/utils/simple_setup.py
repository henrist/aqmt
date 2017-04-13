#!/usr/bin/env python3
#
# This script configures the network so that you can run manual
# traffic on it.

# add path to library root
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from framework.test_framework import Logger, Testbed

if __name__ == '__main__':
    testbed = Testbed()

    testbed.bitrate = 1*1000*10000

    testbed.rtt_clients = 0  # in ms
    testbed.rtt_servera = 15  # in ms
    testbed.rtt_serverb = 15  # in ms

    testbed.netem_clients_params = ""
    testbed.netem_servera_params = ""
    testbed.netem_serverb_params = ""

    testbed.aqm('pie', 'ecn')
    testbed.aqm('pi2')
    testbed.aqm('pfifo_qsize')

    testbed.cc('a', 'cubic', Testbed.ECN_ALLOW)
    testbed.cc('b', 'cubic', Testbed.ECN_INITIATE)

    testbed.reset(log_level=Logger.INFO)
    testbed.setup(log_level=Logger.INFO)

    print(testbed.get_setup())
