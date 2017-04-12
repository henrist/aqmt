#!/usr/bin/env python3

# add path to library root
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from framework.test_framework import Testbed, TestEnv, require_on_aqm_node
from framework.test_utils import MBIT, Step, run_test
import time
from utils import hostname

def test(result_folder):

    def my_test(testcase):
        testdef = testcase.testenv.testdef

        for i in range(15):
            testcase.run_greedy(node='a', tag='node-a')
            testcase.run_greedy(node='b', tag='node-b')

        if testdef.udp_rate > 0:
            time.sleep(1)
            testcase.run_udp(node='a', bitrate=testdef.udp_rate * MBIT, ect='nonect', tag='udp-rate')

    testbed = Testbed()

    testbed.ta_samples = 300
    testbed.ta_idle = 5
    testbed.ta_delay = 250

    testbed.cc('a', 'cubic', testbed.ECN_ALLOW)
    testbed.cc('b', 'dctcp-drop', testbed.ECN_INITIATE)

    run_test(
        folder=result_folder,
        title='Testing VM',
        subtitle='Using 15 flows of CUBIC, 15 flows of DCTCP (with ECN) and 1 flow UDP',
        testenv=TestEnv(testbed, retest=False),
        steps=(
            Step.plot_compare(),
            Step.branch_runif([
                ('simula', lambda testenv: hostname() == 'ford', 'Simula testbed'),
                ('x250', lambda testenv: hostname() == 'DARASK-X250', 'Henriks laptop'),
                ('dqa', lambda testenv: hostname() == 'dual-queue-aqm', 'KVM host'),
            ]),
            Step.branch_sched([
                ('pi2',
                    'PI2: dc_dualq dc_ecn target 15ms tupdate 15ms alpha 5 beta 50 k 2 t\\\\_shift 30ms l\\\\_drop 100',
                    lambda testbed: testbed.aqm_pi2(params='dc_dualq dc_ecn target 15ms tupdate 15ms alpha 5 beta 50 k 2 t_shift 30ms l_drop 100')),
                ('pie', 'PIE', lambda testbed: testbed.aqm_pie('ecn target 15ms tupdate 15ms alpha 1 beta 10 ecndrop 25')),
                #('pfifo', 'pfifo', lambda testbed: testbed.aqm_pfifo()),
            ]),
            Step.branch_rtt([
                10,
                100,
            ]),
            Step.branch_bitrate([
                100,
                250,
                500,
            ]),
            Step.branch_define_udp_rate([
                50,
                300,
            ]),
            Step.branch_repeat(8),
            my_test,
        ),
    )

if __name__ == '__main__':
    require_on_aqm_node()

    result_folder = 'results/vm'
    if len(sys.argv) >= 2:
        result_folder = sys.argv[1]

    test(result_folder)
