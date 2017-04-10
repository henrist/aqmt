#!/usr/bin/env python3

# add path to library root
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from framework.plot import PlotAxis
from framework.test_framework import Testbed, TestEnv, require_on_aqm_node
from framework.test_utils import Step, run_test
import time

def test():

    def custom_cc(testdef):
        # no yield as we don't cause a new branch
        testdef.testbed.cc('a', 'cubic', testbed.ECN_ALLOW)
        testdef.flows_a_tag = 'CUBIC (no ECN)'
        if testdef.testbed.aqm_name in ['pi2']:
            testdef.testbed.cc('b', 'dctcp-drop', testbed.ECN_INITIATE)
            testdef.flows_b_tag = 'DCTCP (ECN)'
        else:
            testdef.testbed.cc('b', 'cubic', testbed.ECN_INITIATE)
            testdef.flows_b_tag = 'ECN-CUBIC'
        yield

    def branch_flow_set(flow_list):
        def branch(testdef):
            for flows_a_num, flows_b_num in flow_list:
                testdef.flows_a_num = flows_a_num
                testdef.flows_b_num = flows_b_num
                yield {
                    'tag': 'flow-%d-%d' % (flows_a_num, flows_b_num),
                    'title': '%d x %s vs %d x %s' % (
                        flows_a_num,
                        testdef.flows_a_tag,
                        flows_b_num,
                        testdef.flows_b_tag,
                    ),
                    'titlelabel': 'Flow combination',
                }
        return branch

    def branch_udp_ect(ect_set):
        def branch(testdef):
            for udp_node, udp_ect, udp_ect_tag in ect_set:
                testdef.udp_node = udp_node
                testdef.udp_ect = udp_ect
                testdef.udp_ect_tag = udp_ect_tag

                yield {
                    'tag': 'udp-%s' % udp_ect,
                    'title': udp_ect_tag,
                    'titlelabel': 'UDP ECT mode',
                }
        return branch

    def my_test(testcase):
        testdef = testcase.testenv.testdef

        for x in range(testdef.flows_a_num):
            testcase.run_greedy(node='a', tag=testdef.flows_a_tag)

        for x in range(testdef.flows_b_num):
            testcase.run_greedy(node='b', tag=testdef.flows_b_tag)

        if testdef.udp_rate > 0:
            time.sleep(1)
            testcase.run_udp(
                node=testdef.udp_node,
                bitrate=testdef.udp_rate * MBIT,
                ect=testdef.udp_ect,
                tag=testdef.udp_ect_tag,
            )

    testbed = Testbed()

    testbed.bitrate = 500 * MBIT

    testbed.ta_samples = 30
    testbed.ta_idle = 5
    testbed.ta_delay = 500

    #testbed.cc('a', 'cubic', testbed.ECN_ALLOW)
    #testbed.cc('b', 'dctcp-drop', testbed.ECN_INITIATE)

    run_test(
        folder='results/sigcomm17-20170405-1',
        title='Sigcomm 17',
        subtitle='Testrate: 500 Mb/s',
        testenv=TestEnv(testbed, retest=False),
        steps=(
            Step.plot_compare(
                utilization_tags=True,
                utilization_queues=True,
                swap_levels=[],
                x_axis=PlotAxis.LOGARITHMIC,
            ),
            Step.branch_rtt([
                2,
                10,
                50,
            ]),
            Step.branch_sched([
                # tag, title, fn
                #('pi2',
                #    'PI2: l4s_dualq l4s_ecn target 15ms tupdate 15ms alpha 5 beta 50 sojourn k 2 t\\\\_shift 30ms l\\\\_drop 100',
                #    lambda testbed: testbed.aqm_pi2(params='l4s_dualq l4s_ecn target 15ms tupdate 15ms alpha 5 beta 50 sojourn k 2 t_shift 30ms l_drop 100')),
                #('pie', 'PIE', lambda testbed: testbed.aqm_pie('ecn target 15ms tupdate 15ms alpha 1 beta 10 ecndrop 25')),
                ('pfifo', 'pfifo', lambda testbed: testbed.aqm_pfifo()),
            ]),
            custom_cc,
            branch_flow_set([
                # num normal in a, num normal in b
                [0, 1],
                [1, 0],
                [1, 1],
                [1, 2],
                [2, 1],
                [5, 5],
                [10, 10],
            ]),
            branch_udp_ect([
                # node, tag/flag, title
                ['a', 'nonect', 'UDP=Non ECT'],
                ['b', 'ect1', 'UDP=ECT(1)'],
            ]),
            Step.branch_define_udp_rate([x + 400 for x in [
                50,
                70,
                75,
                80,
                85,
                86,
                87,
                88,
                89,
                90,
                91,
                92,
                93,
                94,
                95,
                96,
                96.5,
                97,
                97.5,
                98,
                #98.5,
                99,
                99.5,
                100,
                #100.5,
                101,
                102,
                #103,
                104,
                #105,
                106,
                #107,
                108,
                #109,
                110,
                #111,
                112,
                #113,
                114,
                #115,
                116,
                #117,
                118,
                #119,
                120,
                #121,
                122,
                #123,
                124,
                #125,
                126,
                #127,
                128,
                #129,
                130,
                #131,
                132,
                #133,
                134,
                #135,
                136,
                #137,
                138,
                #139,
                140,
                150,
                #160,
                #170,
                #180,
                #190,
                200,
                #225,
                #250,
                #300,
                #350,
                #400,
                #500,
                #600,
                #800,
            ]], title='%d'),
            my_test,
        ),
    )


if __name__ == '__main__':
    require_on_aqm_node()
    test()
