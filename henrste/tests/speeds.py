#!/usr/bin/env python3

# add path to library root
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from framework.test_framework import Testbed, TestEnv, require_on_aqm_node
from framework.test_utils import MBIT, Step, run_test

def test():
    """
    Test one UDP-flow vs TCP-greedy flows) with different UDP speeds and UDP ECT-flags
    """
    testbed = Testbed()
    testbed.bitrate = 10 * MBIT
    testbed.rtt_servera = 25
    testbed.rtt_serverb = 25

    testbed.ta_samples = 60
    testbed.ta_delay = 500

    def branch_custom_cc(cc_set):
        def step(testdef):
            for cctag, cctitle, cc1n, node1, cc1, ecn1, cctag1, cc2n, node2, cc2, ecn2, cctag2 in cc_set:
                testdef.testbed.cc(node1, cc1, ecn1)
                testdef.testbed.cc(node2, cc2, ecn2)

                testdef.cc1n = cc1n
                testdef.cc2n = cc2n
                testdef.node1 = node1
                testdef.node2 = node2
                testdef.cctag1 = cctag1
                testdef.cctag2 = cctag2

                yield {
                    'tag': 'cc-%s' % cctag,
                    'title': cctitle,
                    'titlelabel': 'Congestion control setup',
                }
        return step

    def branch_ect(ect_set):
        def step(testdef):
            for ect, title in ect_set:
                testdef.ect = ect

                yield {
                    'tag': 'ect-%s' % ect,
                    'title': title,
                    'titlelabel': '',
                }
        return step

    def my_test(testcase):
        testdef = testcase.testenv.testdef

        for i in range(testdef.cc1n):
            testcase.run_greedy(node=testdef.node1, tag=testdef.cctag1)

        for i in range(testdef.cc2n):
            testcase.run_greedy(node=testdef.node2, tag=testdef.cctag2)

        testcase.run_udp(node='a', bitrate=testdef.udp_rate*MBIT, ect=testdef.ect, tag='Unresponsive UDP')

    run_test(
        folder='results/speeds',
        title='Overload with UDP (rtt=%d ms, rate=10 Mbit)' % testbed.rtt_servera,
        testenv=TestEnv(testbed),
        steps=[
            Step.plot_compare(
                swap_levels=[1],
                utilization_tags=True,
            ),
            branch_custom_cc([
                # cctag, cctitle, cc1n, node1, cc1, ecn1, cctag1, cc2n, node2, cc2, ecn2, cctag2
                #('dctcp', 'Only DCTCP for TCP', 0, 'a', 'cubic', testbed.ECN_ALLOW, 'TCP', 1, 'b', 'dctcp-drop', testbed.ECN_INITIATE, 'TCP'),
                #('cubic', 'Only Cubic for TCP', 1, 'a', 'cubic', testbed.ECN_ALLOW, 'TCP', 0, 'b', 'dctcp-drop', testbed.ECN_INITIATE, 'TCP'),
                ('mixed', 'Mixed DCTCP (ECN) + Cubic (no ECN) for TCP', 1, 'a', 'cubic', testbed.ECN_ALLOW, 'Cubic', 1, 'b', 'dctcp-drop', testbed.ECN_INITIATE, 'DCTCP'),
            ]),
            Step.branch_sched([
                ('pi2', 'PI2 l\\\\_thresh=1000', lambda testbed: testbed.aqm_pi2(params='l_thresh 1000')),
                ('pie', 'PIE', lambda testbed: testbed.aqm_pie()),
                ('pfifo', 'pfifo', lambda testbed: testbed.aqm_pfifo()),
            ]),
            branch_ect([
                ('nonect', 'UDP with Non-ECT'),
                ('ect1', 'UDP with ECT(1)'),
            ]),
            Step.branch_define_udp_rate([
                2.5,
                5,
                8,
                8.5,
                9,
                9.25,
                9.5,
                9.6,
                9.7,
                9.8,
                9.9,
                10,
                10.1,
                #10.2,
                #10.3,
                #10.4,
                #10.5,
                11,
                #12,
                #12.5,
                #13,
                #13.1,
                #13.2,
                #13.4,
                #13.5,
                #14,
                20,
                40,
                #50,
                #500,
            ], title='%g'),
            my_test,
        ],
    )

if __name__ == '__main__':
    require_on_aqm_node()
    test()
