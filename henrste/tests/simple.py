#!/usr/bin/env python3

# add path to library root
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from framework import Testbed, TestEnv, run_test, steps
from framework.plot import collection_components, flow_components
from framework.traffic import greedy


def test(result_folder):

    def my_test(testcase):
        testcase.traffic(greedy, node='a', tag='CUBIC')
        #testcase.traffic(greedy, node='b', tag='ECN-CUBIC')
        testcase.traffic(greedy, node='b', tag='DCTCP')

    testbed = Testbed()

    testbed.ta_samples = 300
    #testbed.ta_idle = 0
    testbed.ta_delay = 250

    testbed.cc('a', 'cubic', testbed.ECN_ALLOW)
    #testbed.cc('b', 'cubic', testbed.ECN_INITIATE)
    testbed.cc('b', 'dctcp-drop', testbed.ECN_INITIATE)

    run_test(
        folder=result_folder,
        title='Just a simple test to verify setup',
        testenv=TestEnv(testbed, retest=False, reanalyze=False),
        steps=(
            steps.plot_compare(swap_levels=[], components=[
                collection_components.utilization_tags(),
                collection_components.window_rate_ratio(),
                collection_components.window_rate_ratio(y_logarithmic=True),
                collection_components.queueing_delay(),
                collection_components.drops_marks(),
            ]),
            steps.plot_flows(swap_levels=[], components=[
                flow_components.utilization_queues(),
                flow_components.rate_per_flow(),
                flow_components.rate_per_flow(y_logarithmic=True),
                flow_components.window(),
                flow_components.window(y_logarithmic=True),
                flow_components.queueing_delay(),
                flow_components.queueing_delay(y_logarithmic=True),
                flow_components.drops_marks(),
                flow_components.drops_marks(y_logarithmic=True),
            ]),
            steps.branch_sched([
                # tag, title, name, params
                ('pi2',
                    'PI2: dc_dualq dc_ecn target 15ms tupdate 15ms alpha 5 beta 50 k 2 t\\\\_shift 30ms l\\\\_drop 100',
                    'pi2', 'dc_dualq dc_ecn target 15ms tupdate 15ms alpha 5 beta 50 k 2 t_shift 30ms l_drop 100'),
                #('pie', 'PIE', 'pie', 'ecn target 15ms tupdate 15ms alpha 1 beta 10 ecndrop 25'),
                #('pfifo', 'pfifo', 'pfifo', ''),
            ]),
            steps.branch_bitrate([
                10,
                #100,
            ]),
            steps.branch_rtt([
                #2,
                10,
                #50,
                #100,
            ], title='%d'),
            steps.branch_repeat(3),
            #steps.skipif(lambda testenv: False),
            my_test,
        )
    )

if __name__ == '__main__':
    result_folder = 'results/simple'
    if len(sys.argv) >= 2:
        result_folder = sys.argv[1]

    test(result_folder)
