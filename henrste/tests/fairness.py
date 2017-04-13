#!/usr/bin/env python3

# add path to library root
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from framework import Testbed, TestEnv, run_test, steps
from framework.traffic import greedy


def test():
    """
    Test different combinations of congestion controls on different qdiscs

    - Single flows in different congestion controls
    - No overload
    """
    testbed = Testbed()
    testbed.bitrate = 10 * MBIT
    testbed.aqm('pi2')
    testbed.rtt_servera = 25
    testbed.rtt_serverb = 25
    testbed.cc('a', 'cubic', testbed.ECN_ALLOW)
    testbed.cc('b', 'dctcp', testbed.ECN_INITIATE)

    testbed.ta_samples = 250
    testbed.ta_delay = 1000

    def branch_cc_matrix(cc_matrix_set):
        def step(testdef):
            for cctag, cctitle, node1, cc1, ecn1, cctag1, node2, cc2, ecn2, cctag2 in cc_matrix_set:
                testdef.cctag1 = cctag1
                testdef.cctag2 = cctag2

                testdef.testbed.cc(node1, cc1, ecn1)
                testdef.testbed.cc(node2, cc2, ecn2)

                yield {
                    'tag': 'cc-matrix-%s' % cctag,
                    'title': cctitle,
                    'titlelabel': '',
                }
        return step

    def my_test(testcase):
        testdef = testcase.testenv.testdef

        testcase.traffic(greedy, node='a', tag=testdef.cctag1)
        testcase.traffic(greedy, node='b', tag=testdef.cctag2)

    run_test(
        folder='results/fairness',
        title='Testing traffic fairness',
        testenv=TestEnv(testbed),
        steps=[
            steps.plot_compare(
                swap_levels=[0],
                utilization_queues=False,
                utilization_tags=True,
            ),
            steps.branch_sched([
                # tag, title, name, params
                ('pie', 'PIE', 'pie', ''),
                ('pi2', 'PI2\\nl\\\\_thresh=1000', 'pi2', 'l_thresh 1000'),
                ('pi2-l_thresh-10000', 'PI2\\nl\\\\_thresh=10000', 'pi2', 'l_thresh 10000'),
                ('pi2-l_thresh-50000', 'PI2\\nl\\\\_thresh=50000', 'pi2', 'l_thresh 50000'),
                #('pfifo', 'pfifo', 'pfifo', ''),
            ]),
            branch_cc_matrix([
                #['reno-vs-reno', 'Reno/Reno', 'a', 'reno', testbed.ECN_ALLOW, 'Reno', 'b', 'reno', testbed.ECN_ALLOW, 'Reno 2nd'],
                ['reno-vs-dctcp', 'Reno/DCTCP', 'a', 'reno', testbed.ECN_ALLOW, 'Reno', 'b', 'dctcp', testbed.ECN_INITIATE, 'DCTCP'],
                ['reno-vs-cubic', 'Reno/Cubic', 'a', 'reno', testbed.ECN_ALLOW, 'Reno', 'b', 'cubic', testbed.ECN_ALLOW, 'Cubic'],
                #['cubic-vs-cubic', 'Cubic/Cubic', 'a', 'cubic', testbed.ECN_ALLOW, 'Cubic', 'b', 'cubic', testbed.ECN_ALLOW, 'Cubic 2nd'],
                ['cubic-vs-dctcp', 'Cubic/DCTCP', 'a', 'cubic', testbed.ECN_ALLOW, 'Cubic', 'b', 'dctcp', testbed.ECN_INITIATE, 'DCTCP'],
                ['cubic-vs-cubic-ecn', 'Cubic/CubECN', 'a', 'cubic', testbed.ECN_ALLOW, 'Cubic', 'b', 'cubic', testbed.ECN_INITIATE, 'Cubic-ECN'],
                ['dctcp-vs-dctcp', 'DCTCP/DCTCP', 'a', 'dctcp', testbed.ECN_INITIATE, 'DCTCP', 'b', 'dctcp', testbed.ECN_INITIATE, 'DCTCP 2nd'],
            ]),
            steps.skipif(
                lambda testenv: testenv.testdef.sched_tag == 'pi2-l_thresh-50000' and \
                    testenv.testdef.cctag != 'dctcp-vs-dctcp' and \
                    testenv.testdef.cctag != 'cubic-vs-dctcp'
            ),
            steps.branch_rtt([
                2,
                20,
                100,
                200,
            ])
        ],
    )

if __name__ == '__main__':
    test()
