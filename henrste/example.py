#!/usr/bin/env python3
from framework.test_framework import Testbed, TestEnv, TestCase, TestCollection, require_on_aqm_node
MBIT=1000*1000

def example():
    testbed = Testbed()
    testbed.bitrate = 10 * MBIT
    testbed.aqm_pie()
    testbed.cc('a', 'cubic', testbed.ECN_ALLOW)
    testbed.cc('b', 'dctcp', testbed.ECN_INITIATE)
    testbed.ta_samples = 30  # the number of samples in each test

    collection1 = TestCollection('results/example', TestEnv(), title='Example test',
                                 subtitle='Linkrate: 10 Mbit, AQM: PIE')

    for foldername, title, flowcount in [('flows-1', '1 flow each', 1),
                                         ('flows-2', '2 flows each', 2)]:
        # create the TestCollection for this flow number
        collection2 = TestCollection(foldername, title=title, parent=collection1)

        for rtt in [10, 50, 200]:
            testbed.rtt_servera = testbed.rtt_serverb = rtt

            # define the function that will run some traffic in each test
            def my_test(testcase):
                for i in range(flowcount):
                    testcase.run_greedy(node='a', tag='cubic')
                    testcase.run_greedy(node='b', tag='dctcp')

            # run a test with the current flowcount and rtt
            collection2.run_test(my_test, testbed, tag='rtt-%d' % rtt, title=rtt, titlelabel='RTT')

        collection2.plot()
    collection1.plot()

if __name__ == '__main__':
    require_on_aqm_node()
    example()
