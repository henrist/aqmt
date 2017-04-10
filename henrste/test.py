#!/usr/bin/env python3

from framework.test_framework import Testbed, TestEnv, TestCase, TestCollection, require_on_aqm_node
import time

MBIT=1000*1000

def base_testbed():
    testbed = Testbed()
    testbed.bitrate = 10 * MBIT
    testbed.aqm_pi2()
    testbed.rtt_servera = 25
    testbed.rtt_serverb = 25
    testbed.cc('a', 'cubic', testbed.ECN_ALLOW)
    testbed.cc('b', 'dctcp', testbed.ECN_INITIATE)
    return testbed

def test_speeds():
    """Test one UDP-flow vs TCP-greedy flows) with different UDP speeds and UDP ECT-flags"""
    testbed = base_testbed()
    testbed.ta_samples = 60
    testbed.ta_delay = 500

    collection1 = TestCollection('results/speeds', TestEnv(), title='Overload with UDP (rtt=%d ms, rate=10 Mbit)' % testbed.rtt_servera)

    cc_set = [
        #['dctcp', 'Only DCTCP for TCP', 0, 'a', 'cubic', testbed.ECN_ALLOW, 'TCP', 1, 'b', 'dctcp', testbed.ECN_INITIATE, 'TCP'],
        #['cubic', 'Only Cubic for TCP', 1, 'a', 'cubic', testbed.ECN_ALLOW, 'TCP', 0, 'b', 'dctcp', testbed.ECN_INITIATE, 'TCP'],
        ['mixed', 'Mixed DCTCP (ECN) + Cubic (no ECN) for TCP', 1, 'a', 'cubic', testbed.ECN_ALLOW, 'Cubic', 1, 'b', 'dctcp', testbed.ECN_INITIATE, 'DCTCP'],
    ]

    aqm_set = [
        ['pi2', 'PI2 l\\\\_thresh=1000', lambda: testbed.aqm_pi2(params='l_thresh 1000 sojourn')],
        ['pie', 'PIE', lambda: testbed.aqm_pie()],
        ['pfifo', 'pfifo', lambda: testbed.aqm_pfifo()],
    ]

    ect_set = [
        ('nonect', 'UDP with Non-ECT'),
        ('ect1', 'UDP with ECT(1)'),
    ]

    for cctag, cctitle, cc1n, node1, cc1, ecn1, cctag1, cc2n, node2, cc2, ecn2, cctag2 in cc_set:
        testbed.cc(node1, cc1, ecn1)
        testbed.cc(node2, cc2, ecn2)

        collection2 = TestCollection(folder=cctag, parent=collection1, title=cctitle)

        for aqmtag, aqmtitle, aqmfn in aqm_set:
            aqmfn()
            collection3 = TestCollection(folder=aqmtag, parent=collection2, title=aqmtitle)

            for ect, title in ect_set:
                collection4 = TestCollection(ect, parent=collection3, title=title)

                speeds = [
                    2500,
                    5000,
                    8000,
                    8500,
                    9000,
                    9250,
                    9500,
                    9600,
                    9700,
                    9800,
                    9900,
                    10000,
                    10100,
                    #10200,
                    #10300,
                    #10400,
                    #10500,
                    11000,
                    #12000,
                    #12500,
                    #13000,
                    #13100,
                    #13200,
                    #13400,
                    #13500,
                    #14000,
                    20000,
                    40000,
                    #50000,
                    #500000,
                ]

                for speed in speeds:
                    def my_test(testcase):
                        for i in range(cc1n):
                            testcase.run_greedy(node=node1, tag=cctag1)

                        for i in range(cc2n):
                            testcase.run_greedy(node=node2, tag=cctag2)

                        testcase.run_udp(node='a', bitrate=speed*1000, ect=ect, tag='Unresponsive UDP')

                    collection4.run_test(my_test, testbed, tag=speed, title=speed, titlelabel='UDP bitrate [kb/s]')
                collection4.plot_tests_merged()

    collection1.plot(utilization_queues=True, utilization_tags=True, swap_levels=[1])


def test_fairness():
    """Test different combinations of congestion controls on different qdiscs

    - Single flows in different congestion controls
    - No overload
    """
    testbed = base_testbed()
    testbed.ta_samples = 250
    testbed.ta_delay = 1000

    aqms = [
        ['pie', 'PIE', lambda: testbed.aqm_pie()],
        ['pi2', 'PI2\\nl\\\\_thresh=1000', lambda: testbed.aqm_pi2(params='l_thresh 1000 sojourn')],
        ['pi2-l_thresh-10000', 'PI2\\nl\\\\_thresh=10000', lambda: testbed.aqm_pi2(params='l_thresh 10000 sojourn')],
        ['pi2-l_thresh-50000', 'PI2\\nl\\\\_thresh=50000', lambda: testbed.aqm_pi2(params='l_thresh 50000 sojourn')],
        #['pfifo', 'pfifo', lambda: testbed.aqm_pfifo()],
    ]

    cc_matrix = [
        #['reno-vs-reno', 'Reno/Reno', 'a', 'reno', testbed.ECN_ALLOW, 'Reno', 'b', 'reno', testbed.ECN_ALLOW, 'Reno 2nd'],
        ['reno-vs-dctcp', 'Reno/DCTCP', 'a', 'reno', testbed.ECN_ALLOW, 'Reno', 'b', 'dctcp', testbed.ECN_INITIATE, 'DCTCP'],
        ['reno-vs-cubic', 'Reno/Cubic', 'a', 'reno', testbed.ECN_ALLOW, 'Reno', 'b', 'cubic', testbed.ECN_ALLOW, 'Cubic'],
        #['cubic-vs-cubic', 'Cubic/Cubic', 'a', 'cubic', testbed.ECN_ALLOW, 'Cubic', 'b', 'cubic', testbed.ECN_ALLOW, 'Cubic 2nd'],
        ['cubic-vs-dctcp', 'Cubic/DCTCP', 'a', 'cubic', testbed.ECN_ALLOW, 'Cubic', 'b', 'dctcp', testbed.ECN_INITIATE, 'DCTCP'],
        ['cubic-vs-cubic-ecn', 'Cubic/CubECN', 'a', 'cubic', testbed.ECN_ALLOW, 'Cubic', 'b', 'cubic', testbed.ECN_INITIATE, 'Cubic-ECN'],
        ['dctcp-vs-dctcp', 'DCTCP/DCTCP', 'a', 'dctcp', testbed.ECN_INITIATE, 'DCTCP', 'b', 'dctcp', testbed.ECN_INITIATE, 'DCTCP 2nd'],
    ]

    rtts = [2, 20, 100, 200]

    collection1 = TestCollection('results/fairness-sojourn', TestEnv(reanalyze=False, dry_run=False), title='Testing traffic fairness')

    for aqmtag, aqmtitle, aqmfn in aqms:
        aqmfn()
        collection2 = TestCollection(folder=aqmtag, parent=collection1, title=aqmtitle)

        for cctag, cctitle, node1, cc1, ecn1, cctag1, node2, cc2, ecn2, cctag2 in cc_matrix:
            if aqmtag == 'pi2-l_thresh-50000' and cctag != 'dctcp-vs-dctcp' and cctag != 'cubic-vs-dctcp':
                continue

            testbed.cc(node1, cc1, ecn1)
            testbed.cc(node2, cc2, ecn2)

            collection3 = TestCollection(folder=cctag, parent=collection2, title=cctitle)

            for rtt in rtts:
                testbed.rtt_servera = testbed.rtt_serverb = rtt

                def my_test(testcase):
                    testcase.run_greedy(node='a', tag=cctag1)
                    testcase.run_greedy(node='b', tag=cctag2)

                collection3.run_test(my_test, testbed, tag='rtt-%d' % rtt, title=rtt, titlelabel='RTT')

            collection3.plot(utilization_queues=False, utilization_tags=True)
        collection2.plot(utilization_queues=False, utilization_tags=True)
    collection1.plot(utilization_queues=False, utilization_tags=True, swap_levels=[0])


def test_dctth_paper():
    """Testing similar to page 8 of the DCttH-paper"""
    testbed = base_testbed()
    testbed.ta_samples = 250
    testbed.ta_delay = 1000
    #testbed.ta_idle = 0

    bitrates = [
        ['4mbit', '4 mbit', 4*1000*1000],
        ['12mbit', '12 mbit', 12*1000*1000],
        ['40mbit', '40 mbit', 40*1000*1000],
        ['120mbit', '120 mbit', 120*1000*1000],
        ['200mbit', '200 mbit', 200*1000*1000],
    ]

    aqms = [
        ['pie', 'PIE', lambda: testbed.aqm_pie()],
        ['pi2-t_shift-40000', 'PI2 (t\\\\_shift=40000)', lambda: testbed.aqm_pi2(params='t_shift 40000 sojourn')],
    ]

    cc_matrix = [
        ['cubic-vs-dctcp', 'Cubic/DCTCP', 'a', 'cubic', testbed.ECN_ALLOW, 'Cubic', 'b', 'dctcp', testbed.ECN_INITIATE, 'DCTCP'],
        ['cubic-vs-cubic-ecn', 'Cubic/ECN-Cubic', 'a', 'cubic', testbed.ECN_ALLOW, 'Cubic', 'b', 'cubic', testbed.ECN_INITIATE, 'ECN-Cubic'],
    ]

    rtts = [
        2, # extra, not in paper
        5, 10, 20, 50, 100,
    ]

    collection1 = TestCollection('results/dctth-paper-page-8', TestEnv(), title='Testing similar to page 8 of DCttH paper')

    for aqmtag, aqmtitle, aqmfn in aqms:
        aqmfn()
        collection2 = TestCollection(folder=aqmtag, parent=collection1, title=aqmtitle)

        for cctag, cctitle, node1, cc1, ecn1, cctag1, node2, cc2, ecn2, cctag2 in cc_matrix:
            if aqmtag == 'pie' and cctag == 'cubic-vs-dctcp':
                continue
            if aqmtag != 'pie' and cctag == 'cubic-vs-cubic-ecn':
                continue

            testbed.cc(node1, cc1, ecn1)
            testbed.cc(node2, cc2, ecn2)

            collection3 = TestCollection(folder=cctag, parent=collection2, title=cctitle)

            for bitratetag, bitratetitle, bitrate in bitrates:
                testbed.bitrate = bitrate

                collection4 = TestCollection(folder=bitratetag, parent=collection3, title=bitratetitle)

                for rtt in rtts:
                    testbed.rtt_servera = testbed.rtt_serverb = rtt

                    def my_test(testcase):
                        testcase.run_greedy(node='a', tag=cctag1)
                        testcase.run_greedy(node='b', tag=cctag2)

                    collection4.run_test(my_test, testbed, tag='rtt-%d' % rtt, title=rtt, titlelabel='RTT')
                    #collection4.run_test(my_test, testbed, tag='rtt-%d-2' % rtt, title=rtt, titlelabel='RTT')

                collection4.plot(utilization_queues=False, utilization_tags=True)
            collection3.plot(utilization_queues=False, utilization_tags=True)
        collection2.plot(utilization_queues=False, utilization_tags=True)
    collection1.plot(utilization_queues=False, utilization_tags=True, swap_levels=[])

def test_max_window():
    """Tests the maximum window size we can achieve

    requirement outside this test:
    - adjust wmem, see set_sysctl_tcp_mem.sh
      (when in Docker, this must be done outside the Docker container)
    """

    testbed = base_testbed()
    testbed.ta_samples = 300
    testbed.ta_delay = 400
    testbed.ta_idle = 0
    testbed.bitrate = 1200 * MBIT
    testbed.aqm_pi2('limit 50000 target 500000 ecn no_scal tupdate 500000 sojourn')
    #testbed.aqm_pfifo()


    cc_set = [
        #('reno', testbed.ECN_ALLOW, 'reno', 'reno'),
        ('cubic', testbed.ECN_INITIATE, 'cubic', 'cubic'),
        #('dctcp', testbed.ECN_INITIATE, 'dctcp', 'dctcp')
    ]

    rtt_set = [
        #50, 100, 200, 400,
        50,
        100,
        200,
        400,
        800,
    ]

    collection1 = TestCollection('results/max-window', TestEnv(retest=False), title='Testing to achieve a high TCP window',
        subtitle='AQM: pi2 ecn no\\\\_scal 500 ms target   testrate: 1,2 Gb/s   sample interval: 400 ms')

    for cc, ecn, foldername, title in cc_set:
        testbed.cc('a', cc, ecn)

        collection2 = TestCollection(foldername, parent=collection1, title=title)

        for rtt in rtt_set:
            testbed.rtt_servera = rtt

            def my_test(testcase):
                testcase.run_greedy(node='a')
                #testcase.run_greedy(node='a')
                #testcase.run_udp(node='a', bitrate=800000000, ect='ect0', tag='UDP')
                #testcase.run_udp(node='a', bitrate=800000000, ect='ect1', tag='UDP')
                #testcase.run_udp(node='a', bitrate=800000000, ect='nonect', tag='UDP')
                #testcase.run_udp(node='a', bitrate=800000000, ect='nonect', tag='UDP')

            collection2.run_test(my_test, testbed, tag='rtt-%d' % rtt, title=rtt, titlelabel='RTT')

        collection2.plot()
    collection1.plot()


if __name__ == '__main__':
    require_on_aqm_node()

    #test_speeds()
    #test_fairness()
    #test_dctth_paper()
    #test_max_window()
    test_sigcomm17()
