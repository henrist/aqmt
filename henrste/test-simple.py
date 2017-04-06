#!/usr/bin/env python3

from framework.test_framework import Testbed, TestEnv, require_on_aqm_node
from framework.test_utils import *

def test_simple():

    def my_test(testcase):
        testcase.run_greedy(node='a', tag='node-a')
        testcase.run_greedy(node='b', tag='node-b')

    testbed = Testbed()

    testbed.ta_samples = 10
    testbed.ta_idle = 2
    testbed.ta_delay = 500

    testbed.cc('a', 'cubic', testbed.ECN_ALLOW)
    testbed.cc('b', 'dctcp-drop', testbed.ECN_INITIATE)

    run_test(
        folder='results/simple',
        title='Just a simple test to verify setup',
        testenv=TestEnv(testbed),
        steps=(
            branch_sched([
                ('pi2',
                    'PI2: dualq target 15ms tupdate 15ms alpha 5 beta 50 sojourn k 2 t\\\\_shift 30ms l\\\\_drop 100',
                    lambda testbed: testbed.aqm_pi2(params='dualq target 15ms tupdate 15ms alpha 5 beta 50 sojourn k 2 t_shift 30ms l_drop 100')),
                ('pie', 'PIE', lambda testbed: testbed.aqm_pie('ecn target 15ms tupdate 15ms alpha 1 beta 10 ecndrop 25')),
                #('pfifo', 'pfifo', lambda testbed: testbed.aqm_pfifo()),
            ]),
            branch_rtt([10, 50, 100], title='%d'),
            plot_swap(),
            branch_runif([
                ('iftest-1', lambda testenv: True, 'if test 1'),
                ('iftest-2', lambda testenv: True, 'if test 2'),
            ]),
            plot_swap(),
            branch_bitrate([100]),
            plot_swap(-2),
            plot_swap(-1),
            branch_repeat(3),
            #step_skipif(lambda testenv: True),
            my_test,
        )
    )

if __name__ == '__main__':
    require_on_aqm_node()
    test_simple()
