#!/usr/bin/env python3

# add path to library root
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from framework.traffic import greedy
from framework.test_framework import Testbed, TestEnv
from framework.test_utils import Step, run_test

def test():

    def my_test(testcase):
        testcase.traffic(greedy, node='a', tag='CUBIC A')
        testcase.traffic(greedy, node='a', tag='CUBIC A')
        testcase.traffic(greedy, node='a', tag='CUBIC A')
        testcase.traffic(greedy, node='b', tag='CUBIC B')
        testcase.traffic(greedy, node='b', tag='CUBIC B')
        testcase.traffic(greedy, node='b', tag='CUBIC B')

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
                # tag, title, name, params
                ('fq-codel-1', 'fq\\\\_codel', 'fq_codel', ''),
            ]),
            Step.branch_rtt([10, 50, 100], title='%d'),
            Step.branch_bitrate([100]),
            my_test,
        )
    )

if __name__ == '__main__':
    test()
