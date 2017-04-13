#!/usr/bin/env python3

# add path to library root
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

import datetime
from framework.plot import PlotAxis
from framework.test_framework import Testbed, TestEnv
from framework.test_utils import Step, run_test

def test():

    def my_test(testcase):
        #testcase.run_greedy(node='a', tag='RENO')
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
    #testbed.cc('a', 'reno', testbed.ECN_ALLOW)
    testbed.cc('b', 'cubic', testbed.ECN_ALLOW)

    run_test(
        folder='results/pfifo/pfifo-%s' % datetime.datetime.utcnow().isoformat(),
        title='Testing pfifo',
        testenv=TestEnv(testbed, retest=True),
        steps=(
            Step.plot_compare(
                utilization_tags=True,
                utilization_queues=False,
                swap_levels=[],
                x_axis=PlotAxis.CATEGORY,
            ),
            Step.plot_flows(),
            Step.branch_sched([
                # tag, title, name, params
                ('pfifo-1', 'pfifo', 'pfifo', 'limit 1000'),
            ]),
            Step.branch_rtt([
                #2,
                #10,
                #20,
                #50,
                #100,
                200,
            ], title='%d'),
            Step.branch_bitrate([
                #100,
                #200,
                500,
            ]),
            my_test,
        )
    )

if __name__ == '__main__':
    test()
