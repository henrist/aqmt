#!/usr/bin/env python3

# add path to library root
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from framework.test_framework import Testbed, TestEnv, require_on_aqm_node
from framework.test_utils import MBIT, Step, run_test

def test():
    """
    Tests the maximum window size we can achieve

    requirement outside this test:
    - adjust wmem:
      ./utils/set_sysctl_tcp_mem.sh 200000
      (when in Docker, this must be done outside the Docker container)
    """

    testbed = Testbed()
    testbed.ta_samples = 600
    testbed.ta_delay = 400
    testbed.ta_idle = 0
    #testbed.bitrate = 1200 * MBIT
    testbed.bitrate = 200 * MBIT

    testbed.netem_clients_params = "limit 200000"
    testbed.netem_servera_params = "limit 200000"
    testbed.netem_serverb_params = "limit 200000"

    #testbed.aqm_pi2('no_dualq classic_ecn limit 200000 target 50000000 tupdate 500000')
    testbed.aqm_pfifo('limit 200000')

    def my_test(testcase):
        testcase.run_greedy(node='a')
        #testcase.run_greedy(node='a')
        #testcase.run_udp(node='a', bitrate=800000000, ect='ect0', tag='UDP')
        #testcase.run_udp(node='a', bitrate=800000000, ect='ect1', tag='UDP')
        #testcase.run_udp(node='a', bitrate=800000000, ect='nonect', tag='UDP')
        #testcase.run_udp(node='a', bitrate=800000000, ect='nonect', tag='UDP')

    run_test(
        folder='results/max-window',
        title='Testing to achieve a high TCP window',
        subtitle='AQM: pfifo   testrate: 200 Mb/s   sample interval: 400 ms',
        testenv=TestEnv(testbed, retest=True),
        steps=[
            Step.plot_compare(),
            Step.plot_flows(),
            Step.branch_custom(
                list=[
                    #('reno', testbed.ECN_ALLOW, 'reno'),
                    ('cubic', testbed.ECN_INITIATE, 'cubic'),
                    #('dctcp', testbed.ECN_INITIATE, 'dctcp'),
                ],
                fn_testdef=lambda testdef, item: testdef.testenv.testbed.cc('a', item[0], item[1]),
                fn_tag=lambda item: item[2],
                fn_title=lambda item: item[2],
            ),
            Step.branch_rtt([
                #50,
                #100,
                #200,
                #400,
                800,
            ]),
            my_test,
        ],
    )

if __name__ == '__main__':
    require_on_aqm_node()
    test()
