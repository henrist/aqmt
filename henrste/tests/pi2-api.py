#!/usr/bin/env python3

# add path to library root
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from framework.test_framework import Testbed, TestEnv, require_on_aqm_node
from framework.test_utils import Step, run_test
from framework.plot import PlotAxis

def test(result_folder):

    def my_test(testcase):
        testcase.run_greedy(node='a', tag='CUBIC')
        testcase.run_greedy(node='b', tag='DCTCP')

    testbed = Testbed()

    testbed.ta_samples = 50
    testbed.ta_idle = 2
    testbed.ta_delay = 500

    testbed.cc('a', 'cubic', testbed.ECN_ALLOW)
    testbed.cc('b', 'dctcp-drop', testbed.ECN_INITIATE)

    run_test(
        folder=result_folder,
        title='Testing new pi2 API',
        testenv=TestEnv(testbed, retest=False),
        steps=(
            Step.plot_flows(swap_levels=[1]),
            Step.plot_compare(swap_levels=[1], x_axis=PlotAxis.LINEAR),
            Step.branch_sched([
                # tag, title, name, params
                ('pi2-1',
                    'PI^2',
                    'pi2', 'target 15ms tupdate 15ms alpha 5 beta 50 k 2 t_shift 30ms l_drop 100 l_thresh 3000'),
                ('pi2-2',
                    'PI^2: no\\\\_ecn',
                    'pi2', 'no_ecn target 15ms tupdate 15ms alpha 5 beta 50 k 2 t_shift 30ms l_drop 100 l_thresh 3000'),
                ('pi2-3',
                    'PI^2: no\\\\_dualq',
                    'pi2', 'no_dualq target 15ms tupdate 15ms alpha 5 beta 50 k 2 t_shift 30ms l_drop 100 l_thresh 3000'),
                ('pi2-4',
                    'PI^2: no\\\\_dualq no\\\\_ecn',
                    'pi2', 'no_dualq no_ecn target 15ms tupdate 15ms alpha 5 beta 50 k 2 t_shift 30ms l_drop 100 l_thresh 3000'),
                ('pi2-5',
                    'PI^2: dc\\\\_ecn',
                    'pi2', 'dc_ecn target 15ms tupdate 15ms alpha 5 beta 50 k 2 t_shift 30ms l_drop 100 l_thresh 3000'),
                ('pi2-6',
                    'PI^2: dc\\\\_dualq dc\\\\_ecn',
                    'pi2', 'dc_dualq dc_ecn target 15ms tupdate 15ms alpha 5 beta 50 k 2 t_shift 30ms l_drop 100 l_thresh 3000'),
            ]),
            Step.branch_rtt([10, 50, 100], title='%d'),
            Step.branch_bitrate([100]),
            #Step.skipif(lambda testenv: testenv.testdef.sched_tag != 'pi2-6' or testenv.testbed.rtt_servera != 100),
            my_test,
        )
    )

if __name__ == '__main__':
    require_on_aqm_node()

    result_folder = 'results/pi2-api'
    if len(sys.argv) >= 2:
        result_folder = sys.argv[1]

    test(result_folder)
