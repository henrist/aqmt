#!/usr/bin/env python3
#
# This script configures the network so that you can run manual
# traffic on it.

from aqmt import Testbed, logger

if __name__ == '__main__':
    testbed = Testbed()

    testbed.bitrate = 10*1000*10000

    testbed.rtt_clients = 0  # in ms
    testbed.rtt_servera = 15  # in ms
    testbed.rtt_serverb = 15  # in ms

    testbed.netem_clients_params = ""
    testbed.netem_servera_params = ""
    testbed.netem_serverb_params = ""

    #testbed.aqm('pie', 'ecn')
    testbed.aqm('pi2', 'dc_dualq dc_ecn')
    #testbed.aqm('pfifo_qsize')

    testbed.cc('a', 'cubic', Testbed.ECN_ALLOW)
    #testbed.cc('b', 'cubic', Testbed.ECN_INITIATE)
    testbed.cc('b', 'dctcp-drop', Testbed.ECN_INITIATE)

    testbed.reset(log_level=logger.INFO)
    testbed.setup(log_level=logger.INFO)

    print(testbed.get_setup())
