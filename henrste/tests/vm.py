#!/usr/bin/env python3

# add path to library root
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from framework import MBIT, Testbed, TestEnv, run_test, steps
from framework.plot import PlotAxis, collection_components
from framework.traffic import greedy, udp
import time
from utils import hostname


def test(result_folder):

    def my_test(testcase):
        testdef = testcase.testenv.testdef

        for i in range(10):
            testcase.traffic(greedy, node='a', tag='CUBIC')
            testcase.traffic(greedy, node='b', tag='DCTCP')

        if testdef.udp_rate > 0:
            time.sleep(1)
            testcase.traffic(udp, node='a', bitrate=testdef.udp_rate * MBIT, ect='nonect', tag='UDP Non-ECT')

    testbed = Testbed()

    testbed.ta_samples = 500
    testbed.ta_idle = 6
    testbed.ta_delay = 125

    testbed.cc('a', 'cubic', testbed.ECN_ALLOW)
    testbed.cc('b', 'dctcp-drop', testbed.ECN_INITIATE)

    run_test(
        folder=result_folder,
        title='Testing VM',
        subtitle='Using 10 flows of CUBIC, 10 flows of DCTCP (with ECN) and 1 flow UDP',
        testenv=TestEnv(testbed, retest=True, reanalyze=True),
        steps=(
            steps.plot_compare(swap_levels=[3,2,1,0,1,2,3,2,1], components=[
                collection_components.utilization_queues(),
                collection_components.utilization_tags(),
                collection_components.window_rate_ratio(y_logarithmic=True),
                collection_components.window_rate_ratio(),
                collection_components.queueing_delay(y_logarithmic=True),
                collection_components.queueing_delay(),
                collection_components.drops_marks(y_logarithmic=True),
                collection_components.drops_marks(),
            ], x_scale=2),
            #steps.plot_flows(),
            steps.branch_runif([
                ('simula', lambda testenv: hostname() == 'ford', 'PHY'),
                ('simula-desktop', lambda testenv: hostname() == 'DARASK-SM', '-SM'),
                ('x250', lambda testenv: hostname() == 'DARASK-X250', 'X250'),
                ('dqa', lambda testenv: hostname() == 'dual-queue-aqm', 'VM'),
            ]),
            steps.branch_sched([
                # tag, title, name, params
                ('pi2',
                    'PI2 dc',
                    'pi2', 'dc_dualq dc_ecn target 15ms tupdate 15ms alpha 5 beta 50 k 2 t_shift 30ms l_drop 100'),
                ('pie', 'PIE', 'pie', 'ecn target 15ms tupdate 15ms alpha 1 beta 10 ecndrop 25'),
                ('pfifo', 'pfifo', 'pfifo', ''),
            ]),
            steps.branch_rtt([
                2,
                10,
                100,
            ], title='%d ms'),
            steps.branch_bitrate([
                100,
                250,
                500,
            ], title='%d', titlelabel='Linkrate [Mb/s]'),
            steps.branch_define_udp_rate([
                50,
                300,
            ], title='%g'),
            steps.plot_flows(),
            steps.branch_repeat(5),
            my_test,
        ),
    )

if __name__ == '__main__':
    result_folder = 'results/vm'
    if len(sys.argv) >= 2:
        result_folder = sys.argv[1]

    test(result_folder)
