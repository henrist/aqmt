#!/usr/bin/env python3

# add path to library root
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from framework import steps
from framework.traffic import greedy
from framework.test_framework import Testbed, TestEnv
from framework.test_utils import run_test

def test():
    """
    Testing similar to page 8 of the DCttH-paper
    """
    testbed = Testbed()
    testbed.ta_samples = 250
    testbed.ta_delay = 1000
    #testbed.ta_idle = 0

    def branch_cc_matrix(cc_matrix_set):
        def step(testdef):
            for cctag, cctitle, node1, cc1, ecn1, cctag1, node2, cc2, ecn2, cctag2 in cc_matrix_set:
                testdef.cctag1 = cctag1
                testdef.cctag2 = cctag2
                testdef.cc_tag = cctag

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
        folder='results/dctth-paper-page-8',
        title='Testing similar to page 8 of DCttH paper',
        testenv=TestEnv(testbed),
        steps=[
            steps.plot_compare(
                utilization_queues=False,
                utilization_tags=True,
            ),
            steps.branch_sched([
                # tag, title, name, params
                ('pie', 'PIE', 'pie', ''),
                ('pi2-t_shift-40000', 'PI2 (t\\\\_shift=40000)', 'pi2', 't_shift 40000'),
            ]),
            branch_cc_matrix([
                ('cubic-vs-dctcp', 'Cubic/DCTCP', 'a', 'cubic', testbed.ECN_ALLOW, 'Cubic', 'b', 'dctcp', testbed.ECN_INITIATE, 'DCTCP'),
                ('cubic-vs-cubic-ecn', 'Cubic/ECN-Cubic', 'a', 'cubic', testbed.ECN_ALLOW, 'Cubic', 'b', 'cubic', testbed.ECN_INITIATE, 'ECN-Cubic'),
            ]),
            steps.skipif(lambda testenv: testenv.testdef.sched_tag == 'pie' and testenv.testdef.cc_tag == 'cubic-vs-dctcp'),
            steps.skipif(lambda testenv: testenv.testdef.sched_tag != 'pie' and testenv.testdef.cc_tag == 'cubic-vs-cubic-ecn'),
            steps.branch_bitrate([
                4,
                12,
                40,
                120,
                200,
            ]),
            steps.branch_rtt([
                2, # extra, not in paper
                5,
                10,
                20,
                50,
                100,
            ]),
            my_test,
        ],
    )

if __name__ == '__main__':
    test()
