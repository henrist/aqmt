#!/usr/bin/env python3

from framework.test_framework import Testbed, TestEnv, TestCase, TestCollection, require_on_aqm_node
from framework.test_utils import MBIT, Step, run_test
import time

def test_speeds():
    """
    Test one UDP-flow vs TCP-greedy flows) with different UDP speeds and UDP ECT-flags
    """
    testbed = Testbed()
    testbed.bitrate = 10 * MBIT
    testbed.aqm_pi2()
    testbed.rtt_servera = 25
    testbed.rtt_serverb = 25
    testbed.cc('a', 'cubic', testbed.ECN_ALLOW)
    testbed.cc('b', 'dctcp', testbed.ECN_INITIATE)

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
            Step.plot_combine(
                swap_levels=[1],
                utilization_tags=True,
            ),
            branch_custom_cc([
                # cctag, cctitle, cc1n, node1, cc1, ecn1, cctag1, cc2n, node2, cc2, ecn2, cctag2
                #('dctcp', 'Only DCTCP for TCP', 0, 'a', 'cubic', testbed.ECN_ALLOW, 'TCP', 1, 'b', 'dctcp', testbed.ECN_INITIATE, 'TCP'),
                #('cubic', 'Only Cubic for TCP', 1, 'a', 'cubic', testbed.ECN_ALLOW, 'TCP', 0, 'b', 'dctcp', testbed.ECN_INITIATE, 'TCP'),
                ('mixed', 'Mixed DCTCP (ECN) + Cubic (no ECN) for TCP', 1, 'a', 'cubic', testbed.ECN_ALLOW, 'Cubic', 1, 'b', 'dctcp', testbed.ECN_INITIATE, 'DCTCP'),
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
            Step.branch_define_udp_bitrate([
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


def test_fairness():
    """
    Test different combinations of congestion controls on different qdiscs

    - Single flows in different congestion controls
    - No overload
    """
    testbed = Testbed()
    testbed.bitrate = 10 * MBIT
    testbed.aqm_pi2()
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

        testcase.run_greedy(node='a', tag=testdef.cctag1)
        testcase.run_greedy(node='b', tag=testdef.cctag2)

    run_test(
        folder='results/fairness',
        title='Testing traffic fairness',
        testenv=TestEnv(testbed),
        steps=[
            Step.plot_compare(
                swap_levels=[0],
                utilization_queues=False,
                utilization_tags=True,
            ),
            Step.branch_sched([
                ['pie', 'PIE', lambda testbed: testbed.aqm_pie()],
                ['pi2', 'PI2\\nl\\\\_thresh=1000', lambda testbed: testbed.aqm_pi2(params='l_thresh 1000')],
                ['pi2-l_thresh-10000', 'PI2\\nl\\\\_thresh=10000', lambda testbed: testbed.aqm_pi2(params='l_thresh 10000')],
                ['pi2-l_thresh-50000', 'PI2\\nl\\\\_thresh=50000', lambda testbed: testbed.aqm_pi2(params='l_thresh 50000')],
                #['pfifo', 'pfifo', lambda testbed: testbed.aqm_pfifo()],
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
            Step.skipif(
                lambda testenv: testenv.testdef.sched_tag == 'pi2-l_thresh-50000' and \
                    testenv.testdef.cctag != 'dctcp-vs-dctcp' and \
                    testenv.testdef.cctag != 'cubic-vs-dctcp'
            ),
            Step.branch_rtt([
                2,
                20,
                100,
                200,
            ])
        ],
    )


def test_dctth_paper():
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
        testcase.run_greedy(node='a', tag=testdef.cctag1)
        testcase.run_greedy(node='b', tag=testdef.cctag2)

    run_test(
        folder='results/dctth-paper-page-8',
        title='Testing similar to page 8 of DCttH paper',
        testenv=TestEnv(testbed),
        steps=[
            Step.plot_compare(
                utilization_queues=False,
                utilization_tags=True,
            ),
            Step.branch_sched([
                ('pie', 'PIE', lambda testbed: testbed.aqm_pie()),
                ('pi2-t_shift-40000', 'PI2 (t\\\\_shift=40000)', lambda testbed: testbed.aqm_pi2(params='t_shift 40000')),
            ]),
            branch_cc_matrix([
                ('cubic-vs-dctcp', 'Cubic/DCTCP', 'a', 'cubic', testbed.ECN_ALLOW, 'Cubic', 'b', 'dctcp', testbed.ECN_INITIATE, 'DCTCP'),
                ('cubic-vs-cubic-ecn', 'Cubic/ECN-Cubic', 'a', 'cubic', testbed.ECN_ALLOW, 'Cubic', 'b', 'cubic', testbed.ECN_INITIATE, 'ECN-Cubic'),
            ]),
            Step.skipif(lambda testenv: testenv.testdef.sched_tag == 'pie' and testenv.testdef.cc_tag == 'cubic-vs-dctcp'),
            Step.skipif(lambda testenv: testenv.testdef.sched_tag != 'pie' and testenv.testdef.cc_tag == 'cubic-vs-cubic-ecn'),
            Step.branch_bitrate([
                4,
                12,
                40,
                120,
                200,
            ]),
            Step.branch_rtt([
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

def test_max_window():
    """
    Tests the maximum window size we can achieve

    requirement outside this test:
    - adjust wmem:
      ./utils/set_sysctl_tcp_mem.sh 200000
      (when in Docker, this must be done outside the Docker container)
    """

    testbed = Testbed()
    testbed.ta_samples = 600
    testbed.ta_delay = 400
    testbed.ta_idle = 0
    #testbed.bitrate = 1200 * MBIT
    testbed.bitrate = 200 * MBIT

    testbed.netem_clients_params = "limit 200000"
    testbed.netem_servera_params = "limit 200000"
    testbed.netem_serverb_params = "limit 200000"

    #testbed.aqm_pi2('no_dualq classic_ecn limit 200000 target 50000000 tupdate 500000')
    testbed.aqm_pfifo('limit 200000')

    def my_test(testcase):
        testcase.run_greedy(node='a')
        #testcase.run_greedy(node='a')
        #testcase.run_udp(node='a', bitrate=800000000, ect='ect0', tag='UDP')
        #testcase.run_udp(node='a', bitrate=800000000, ect='ect1', tag='UDP')
        #testcase.run_udp(node='a', bitrate=800000000, ect='nonect', tag='UDP')
        #testcase.run_udp(node='a', bitrate=800000000, ect='nonect', tag='UDP')

    run_test(
        folder='results/max-window',
        title='Testing to achieve a high TCP window',
        subtitle='AQM: pfifo   testrate: 200 Mb/s   sample interval: 400 ms',
        testenv=TestEnv(testbed),
        steps=[
            Step.plot_compare(),
            Step.plot_flows(),
            Step.branch_custom(
                list=[
                    #('reno', testbed.ECN_ALLOW, 'reno'),
                    ('cubic', testbed.ECN_INITIATE, 'cubic'),
                    #('dctcp', testbed.ECN_INITIATE, 'dctcp'),
                ],
                fn_testdef=lambda testdef, item: testdef.testenv.testbed.cc('a', item[0], item[1]),
                fn_tag=lambda item: item[2],
                fn_title=lambda item: item[2],
            ),
            Step.branch_rtt([
                #50,
                #100,
                #200,
                #400,
                800,
            ]),
            my_test,
        ],
    )


if __name__ == '__main__':
    require_on_aqm_node()

    #test_speeds()
    #test_fairness()
    #test_dctth_paper()
    test_max_window()
