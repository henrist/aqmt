#!/usr/bin/env python3

# add path to library root
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from framework.test_framework import Testbed, TestEnv, require_on_aqm_node
from framework.test_utils import Step, run_test

def test():

    def my_test(testcase):
        testcase.run_greedy(node='a', tag='CUBIC A')
        testcase.run_greedy(node='a', tag='CUBIC A')
        testcase.run_greedy(node='a', tag='CUBIC A')
        testcase.run_greedy(node='b', tag='CUBIC B')
        testcase.run_greedy(node='b', tag='CUBIC B')
        testcase.run_greedy(node='b', tag='CUBIC B')

    testbed = Testbed()

    testbed.ta_samples = 30
    testbed.ta_idle = 2
    testbed.ta_delay = 500

    testbed.cc('a', 'cubic', testbed.ECN_ALLOW)
    testbed.cc('b', 'cubic', testbed.ECN_ALLOW)

    run_test(
        folder='results/fq-codel',
        title='Testing fq_codel',
        testenv=TestEnv(testbed),
        steps=(
            Step.plot_compare(),
            Step.branch_sched([
                ('fq-codel-1',
                    'fq\\\\_codel',
                    lambda testbed: testbed.aqm_fq_codel()),
            ]),
            Step.branch_rtt([10, 50, 100], title='%d'),
            Step.branch_bitrate([100]),
            my_test,
        )
    )

if __name__ == '__main__':
    require_on_aqm_node()
    test()
