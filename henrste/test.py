#!/usr/bin/env python3

from test_framework import Testbed, TestEnv, TestCase, TestCollection, require_on_aqm_node
import time

def base_testbed():
    testbed = Testbed()
    testbed.bitrate = 10*1000*1000
    testbed.aqm_pi2()
    testbed.rtt_servera = 25
    testbed.rtt_serverb = 25
    testbed.cc('a', 'cubic', testbed.ECN_ALLOW)
    testbed.cc('b', 'dctcp', testbed.ECN_INITIATE)
    return testbed

def test_testbed():
    testbed = base_testbed()
    testbed.rtt_servera = testbed.rtt_serverb = 100
    testbed.cc('b', 'dctcp', testbed.ECN_INITIATE)
    testbed.aqm_pi2()

    testbed.reset()
    testbed.setup()
    testbed.print_setup()

def test_cubic():
    testbed = base_testbed()
    collection1 = TestCollection('tests/testsets/cubic', TestEnv(), title='Testing cubic vs other congestion controls',
                                      subtitle='Linkrate: 10 Mbit')

    for aqm, foldername, aqmtitle in [#(testbed.aqm_pi2, 'pi2', 'AQM: pi2'),
                                      (functools.partial(testbed.aqm_pi2, params='l_thresh 50000'), 'pi2-l_thresh-50000', 'AQM: pi2 (l\_thresh = 50000)'),
                                      #(testbed.aqm_fq_codel, 'fq_codel', 'AQM: fq_codel'),
                                      #(testbed.aqm_red, 'red', 'AQM: RED'),
                                      #(testbed.aqm_default, 'no-aqm', 'No AQM'),
                                      ]:

        aqm()
        collection2 = TestCollection(foldername, title=aqmtitle, parent=collection1)

        #for numflows in [1,2,3]:
        for numflows in [1]:
            collection3 = TestCollection('flows-%d' % numflows, title='%d flows each' % numflows, parent=collection2)

            for cc, ecn, foldername, title in [#('cubic', 2, 'cubic',    'cubic vs cubic'),
                                               ('cubic', 1, 'cubic-ecn','cubic vs cubic-ecn'),
                                               ('dctcp', 1, 'dctcp',    'cubic vs dctcp')]:
                testbed.cc_b = cc
                testbed.ecn_b = ecn

                # TODO: missing a TestCollection here....

                #for rtt in [2, 5, 10, 25, 50, 75, 100, 125, 150, 175, 200, 250, 300, 400]:
                for rtt in [5, 10, 25, 50, 100, 200]:
                    testbed.rtt_servera = testbed.rtt_serverb = rtt

                    def my_test(testcase):
                        for i in range(numflows):
                            testcase.run_greedy(node='a')
                            testcase.run_greedy(node='b')

                    collection3.run_test(my_test, testbed, tag=rtt, title=rtt, titlelabel='RTT')
                collection3.plot()
    collection1.plot()

def test_increasing_udp_traffic():
    """Test UDP-traffic in both queues with increasing bandwidth"""
    testbed = base_testbed()
    testbed.ta_delay = 500
    testbed.ta_samples = 60

    collection = TestCollection('tests/testsets/increasing-udp', TestEnv(),
                                title='Testing increasing UDP-rate in same test',
                                subtitle='Look at graphs for the individual tests for this to have any use')

    def my_test(testcase):
        for x in range(10):
            testcase.run_udp(node='a', bitrate=1250000, ect='nonect', tag='UDP Non-ECT')
            testcase.run_udp(node='b', bitrate=1250000, ect='ect0', tag='UDP ECT0')
            time.sleep(2)

    collection.run_test(my_test, testbed, tag='001', title='test 1')
    collection.run_test(my_test, testbed, tag='002', title='test 2')
    collection.run_test(my_test, testbed, tag='003', title='test 3')
    collection.run_test(my_test, testbed, tag='004', title='test 4')
    collection.plot(utilization_queues=False, utilization_tags=True)

def test_speeds():
    """Test one UDP-flow vs one TCP-greedy flow with different UDP speeds and UDP ECT-flags"""
    testbed = base_testbed()
    testbed.ta_samples = 60
    testbed.ta_delay = 500

    collection1 = TestCollection('tests/testsets/speeds', TestEnv(), title='Overload with UDP')

    aqm_set = [
        ['pi2', 'PI2\\nl\\\\_thresh=1000', lambda: testbed.aqm_pi2(params='l_thresh 1000')],
        ['pfifo', 'pfifo', lambda: testbed.aqm_pfifo()],
    ]

    ect_set = [
        ('nonect', 'UDP with Non-ECT'),
        ('ect1', 'UDP with ECT(1)'),
    ]

    for aqmtag, aqmtitle, aqmfn in aqm_set:
        aqmfn()
        collection2 = TestCollection(folder=aqmtag, parent=collection1, title=aqmtitle)

        for ect, title in ect_set:
            collection3 = TestCollection(ect, parent=collection2, title=title)

            speeds = [
                5000,
                #9000,
                9500,
                10000,
                #10500,
                #11000,
                #12000,
                #12500,
                #13000,
                #13100,
                #13200,
                #13400,
                #13500,
                #14000,
                #28000,
                #50000,
                #500000,
            ]

            for speed in speeds:
                def my_test(testcase):
                    testcase.run_greedy(node='b', tag='TCP')
                    testcase.run_udp(node='a', bitrate=speed*1000, ect=ect, tag='Unresponsive UDP')

                collection3.run_test(my_test, testbed, tag=speed, title=speed, titlelabel='UDP bitrate [kb/s]')

            collection3.plot(utilization_queues=False, utilization_tags=True)
        collection2.plot(utilization_queues=False, utilization_tags=True)
    collection1.plot(utilization_queues=False, utilization_tags=True)

def test_many_flows():
    testbed = base_testbed()
    testbed.aqm_pi2()
    testbed.cc('b', 'dctcp', testbed.ECN_INITIATE)
    testbed.ta_samples = 120
    testbed.ta_delay = 50

    collection1 = TestCollection('tests/testsets/many-flows-2', TestEnv(), title='Testing with many flows', subtitle='All tests on pi2 AQM')
    for name, n_a, n_b, title in [#('mixed', 1, 1, 'traffic both machines'),
                                  #('a',     1, 0, 'traffic only a'),
                                  ('b',     0, 1, 'traffic only b')]:

        collection2 = TestCollection(name, parent=collection1, title=title)

        for x in range(1, 3):
            collection3 = TestCollection('test-%d' % x, parent=collection2, title='%d flows' % x)

            def my_test(testcase):
                nonlocal x
                for i in range(x * n_a):
                    testcase.run_greedy(node='a')
                for i in range(x * n_b):
                    testcase.run_greedy(node='b')

            for rtt in [5, 10, 20, 50, 100, 400, 600, 800]:
                testbed.rtt_servera = testbed.rtt_serverb = rtt
                collection3.run_test(my_test, testbed, tag='rtt-%d' % rtt, title=rtt, titlelabel='RTT')

            collection3.plot()
    collection1.plot()

def test_different_cc():
    testbed = base_testbed()
    testbed.ta_samples = 400
    testbed.ta_delay = 50

    collection0 = TestCollection('tests/testsets/different-cc', TestEnv(is_interactive=None, retest=False, replot=False, dry_run=False), title='Testing different congestion controls on its own')

    for l_thresh in [1000, 100000]:
        collection1 = TestCollection('l_thresh-%d' % l_thresh, parent=collection0, title=l_thresh) #title='l\\_thresh=%d' % l_thresh)

        for cc, ecn, foldername, title, aqm_params in [#('reno', testbed.ECN_ALLOW, 'reno',    'reno', ''),
                                                       ('cubic', testbed.ECN_ALLOW, 'cubic',    'cubic', ''),
                                                       ('cubic', testbed.ECN_INITIATE, 'cubic-ecn-noecn-no_scal','cubic-ecn noecn no\\_scal', 'noecn no_scal'),
                                                       ('cubic', testbed.ECN_INITIATE, 'cubic-ecn-ecn-no_scal','cubic-ecn ecn no\\_scal', 'ecn no_scal'),
                                                       ('cubic', testbed.ECN_INITIATE, 'cubic-ecn-dualq-ecn_scal','cubic-ecn dualq ecn\\_scal', 'dualq ecn_scal'),
                                                       ('cubic', testbed.ECN_INITIATE, 'cubic-ecn-dualq_ect1-ecn_scal','cubic-ecn dualq\\_ect1 ecn\\_scal', 'dualq_ect1 ecn_scal'),
                                                       ('cubic', testbed.ECN_INITIATE, 'cubic-ecn-dualq_ect1-ect1_scal','cubic-ecn dualq\\_ect1 ect1\\scal', 'dualq_ect1 ect1_scal'),
                                                       ('cubic', testbed.ECN_INITIATE, 'cubic-ecn-dualq-no_scal','cubic-ecn dualq no\\_scal', 'dualq no_scal'),
                                                       #('cubic', testbed.ECN_INITIATE, 'cubic-ecn-l4s','cubic-ecn-l4s', ''),
                                                       #('dctcp', testbed.ECN_INITIATE, 'dctcp',    'dctcp', ''),
                                                       ]:

            testbed.cc('a', cc, ecn)

            collection2 = TestCollection(foldername, parent=collection1, title=title)
            testbed.aqm_pi2(aqm_params + ' l_thresh %d' % l_thresh)

            #for rtt in [5,10,20,40,80,160,320,640]:
            #for rtt in [40,80,160]:
            for rtt in [2, 20,80]:
                testbed.rtt_servera = testbed.rtt_serverb = rtt
                def my_test(testcase):
                    testcase.run_greedy(node='a')
                collection2.run_test(my_test, testbed, tag='rtt-%d' % rtt, title=rtt, titlelabel='RTT')
                #collection2.run_test(my_test, testbed, tag='rtt-%d-verify1' % rtt, title=rtt, titlelabel='RTT')
                #collection2.run_test(my_test, testbed, tag='rtt-%d-verify2' % rtt, title=rtt, titlelabel='RTT')
            collection2.plot()
        collection1.plot()
    collection0.plot(swap_levels=[0])

def test_scaling_in_classic_queue():
    testbed = base_testbed()
    testbed.ta_samples = 400
    testbed.ta_delay = 50

    collection1 = TestCollection('tests/testsets/scaling-in-classic-queue', TestEnv(is_interactive=None, retest=False, replot=False, dry_run=False), title='Testing scaling ecn traffic in classic queue')

    for cc, ecn, foldername, title, aqm_params in [#('cubic', testbed.ECN_INITIATE, 'cubic-ecn',  'cubic-ecn ', 'noecn ecn_scal'),
                                                   ('dctcp', testbed.ECN_INITIATE, 'dctcp-noecn-no_scal', 'cubic-ecn noecn no\\_scal', 'noecn no_scal'),
                                                   ('dctcp', testbed.ECN_INITIATE, 'dctcp-ecn-no_scal',   'dctcp-ecn ecn no\\_scal',   'ecn no_scal'),
                                                   ('dctcp', testbed.ECN_INITIATE, 'dctcp-ecn-ecn_scal',  'dctcp-ecn ecn ecn\\_scal',  'ecn ecn_scal'),
                                                   ]:
        testbed.cc('a', 'cubic', testbed.ECN_ALLOW)
        testbed.cc('b', cc, ecn)

        collection2 = TestCollection(foldername, parent=collection1, title=title)
        testbed.aqm_pi2(aqm_params)

        #for rtt in [5,10,20,40,80,160,320,640]:
        #for rtt in [40,80,160]:
        for rtt in [2, 20, 80]:
            testbed.rtt_servera = testbed.rtt_serverb = rtt
            def my_test(testcase):
                testcase.run_greedy(node='a')
                testcase.run_greedy(node='b')
            collection2.run_test(my_test, testbed, tag='rtt-%d-test1' % rtt, title=rtt, titlelabel='RTT')
            collection2.run_test(my_test, testbed, tag='rtt-%d-test2' % rtt, title=rtt, titlelabel='RTT')
            collection2.run_test(my_test, testbed, tag='rtt-%d-test3' % rtt, title=rtt, titlelabel='RTT')
        collection2.plot()
    collection1.plot(swap_levels=[0])

def test_fairness():
    """Test different combinations of congestion controls on different qdiscs

    - Single flows in different congestion controls
    - No overload
    """
    testbed = base_testbed()
    testbed.ta_samples = 180
    testbed.ta_delay = 1000

    aqms = [
        ['pie', 'PIE', lambda: testbed.aqm_pie()],
        ['pi2', 'PI2\\nl\\\\_thresh=1000', lambda: testbed.aqm_pi2(params='l_thresh 1000')],
        ['pi2-l_thresh-10000', 'PI2\\nl\\\\_thresh=10000', lambda: testbed.aqm_pi2(params='l_thresh 10000')],
        ['pi2-l_thresh-50000', 'PI2\\nl\\\\_thresh=50000', lambda: testbed.aqm_pi2(params='l_thresh 50000')],
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

    collection1 = TestCollection('tests/testsets/fairness', TestEnv(reanalyze=False, dry_run=False), title='Testing traffic fairness')

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

def test_shifted_fifo():
    """Test different parameters for the shifted fifo"""
    testbed = base_testbed()
    testbed.ta_samples = 60
    testbed.ta_delay = 500

    bitrates = [
        ['10mbit', '10 mbit', 10*1000*1000],
        ['10mbit', '40 mbit', 40*1000*1000],
    ]

    aqms = [
        #['pi2', 'PI2\\nl\\\\_thresh=1000', lambda: testbed.aqm_pi2(params='l_thresh 1000')],
        #['pi2-l_thresh-10000', 'PI2\\nl\\\\_thresh=10000', lambda: testbed.aqm_pi2(params='l_thresh 10000')],
        #['pi2-l_thresh-50000', 'PI2\\nl\\\\_thresh=50000', lambda: testbed.aqm_pi2(params='l_thresh 50000')],
        ['pi2-l_thresh-50000-t_shift-40000', 'PI2\\nl\\\\_thresh=50000 t\\\\_shift=40000', lambda: testbed.aqm_pi2(params='l_thresh 50000 t_shift 40000')],
    ]

    cc_matrix = [
        #['reno-vs-reno', 'Reno/Reno', 'a', 'reno', testbed.ECN_ALLOW, 'Reno', 'b', 'reno', testbed.ECN_ALLOW, 'Reno 2nd'],
        ['reno-vs-dctcp', 'Reno/DCTCP', 'a', 'reno', testbed.ECN_ALLOW, 'Reno', 'b', 'dctcp', testbed.ECN_INITIATE, 'DCTCP'],
        #['reno-vs-cubic', 'Reno/Cubic', 'a', 'reno', testbed.ECN_ALLOW, 'Reno', 'b', 'cubic', testbed.ECN_ALLOW, 'Cubic'],
        #['cubic-vs-cubic', 'Cubic/Cubic', 'a', 'cubic', testbed.ECN_ALLOW, 'Cubic', 'b', 'cubic', testbed.ECN_ALLOW, 'Cubic 2nd'],
        ['cubic-vs-dctcp', 'Cubic/DCTCP', 'a', 'cubic', testbed.ECN_ALLOW, 'Cubic', 'b', 'dctcp', testbed.ECN_INITIATE, 'DCTCP'],
        #['cubic-vs-cubic-ecn', 'Cubic/CubECN', 'a', 'cubic', testbed.ECN_ALLOW, 'Cubic', 'b', 'cubic', testbed.ECN_INITIATE, 'Cubic-ECN'],
        #['dctcp-vs-dctcp', 'DCTCP/DCTCP', 'a', 'dctcp', testbed.ECN_INITIATE, 'DCTCP', 'b', 'dctcp', testbed.ECN_INITIATE, 'DCTCP 2nd'],
    ]

    rtts = [2, 20, 100, 200]

    collection1 = TestCollection('tests/testsets/shifted_fifo', TestEnv(reanalyze=False, dry_run=False), title='Testing shifted fifo')

    for aqmtag, aqmtitle, aqmfn in aqms:
        aqmfn()
        collection2 = TestCollection(folder=aqmtag, parent=collection1, title=aqmtitle)

        for cctag, cctitle, node1, cc1, ecn1, cctag1, node2, cc2, ecn2, cctag2 in cc_matrix:
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

                collection4.plot(utilization_queues=False, utilization_tags=True)
            collection3.plot(utilization_queues=False, utilization_tags=True)
        collection2.plot(utilization_queues=False, utilization_tags=True)
    collection1.plot(utilization_queues=False, utilization_tags=True, swap_levels=[0])


if __name__ == '__main__':
    require_on_aqm_node()

    #test_plot_test_data()
    #test_many_flows()
    #test_testbed()
    #test_cubic()
    #test_increasing_udp_traffic()
    #test_speeds()
    #test_different_cc()
    #test_scaling_in_classic_queue()
    #test_fairness()
    test_shifted_fifo()
