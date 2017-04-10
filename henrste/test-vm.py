#!/usr/bin/env python3

from framework.test_framework import Testbed, TestEnv, require_on_aqm_node
from framework.test_utils import Step, run_test
import time

def test():

    def branch_titles(titles):
        def branch(testdef):
            for tag, title in titles:
                yield {
                    'tag': 'title-%s' % tag,
                    'title': title,
                    'titlelabel': '',
                }
        return branch

    def my_test(testcase):
        testdef = testcase.testenv.testdef

        for i in range(15):
            testcase.run_greedy(node='a', tag='node-a')
            testcase.run_greedy(node='b', tag='node-b')

        if testdef.udp_rate > 0:
            time.sleep(1)
            testcase.run_udp(node='a', bitrate=testdef.udp_rate * MBIT, ect='nonect', tag='udp-rate')

    testbed = Testbed()

    testbed.ta_samples = 30
    testbed.ta_idle = 5
    testbed.ta_delay = 500

    testbed.cc('a', 'cubic', testbed.ECN_ALLOW)
    testbed.cc('b', 'dctcp-drop', testbed.ECN_INITIATE)

    run_test(
        folder='results/vm-test-1',
        title='Testing VM',
        subtitle='Using 15 flows of CUBIC, 15 flows of DCTCP (with ECN) and 1 flow UDP',
        testenv=TestEnv(testbed, retest=False),
        steps=(
            Step.plot_compare(),
            branch_titles([
                ('dqa', 'dqa'),
                ('dqa1', 'dqa1'),
                ('dqa2', 'dqa2'),
                ('dqa3', 'dqa3'),
                ('dqa4', 'dqa4'),
                ('dqa5', 'dqa5'),
                ('x250', 'x250'),
            ]),
            Step.branch_sched([
                ('pi2',
                    'PI2: dc_dualq dc_ecn target 15ms tupdate 15ms alpha 5 beta 50 k 2 t\\\\_shift 30ms l\\\\_drop 100',
                    lambda testbed: testbed.aqm_pi2(params='dc_dualq dc_ecn target 15ms tupdate 15ms alpha 5 beta 50 k 2 t_shift 30ms l_drop 100')),
                ('pie', 'PIE', lambda testbed: testbed.aqm_pie('ecn target 15ms tupdate 15ms alpha 1 beta 10 ecndrop 25')),
                #('pfifo', 'pfifo', lambda testbed: testbed.aqm_pfifo()),
            ]),
            Step.branch_rtt([10]),
            Step.branch_bitrate([100,250,500]),
            Step.branch_define_udp_rate([50]),
            Step.branch_runif([
                #('config-3',      lambda testenv: False, '8 GiB / 6 vCPU'),
                #('config-6144-1', lambda testenv: False, '6 GiB / 1 vCPU'),
                #('config-512-6',  lambda testenv: False, '512 MiB / 6 vCPU'),
                #('config-4',      lambda testenv: False, '512 MiB / 1 vCPU'),
                #('config-3072-2', lambda testenv: False,  '3 GiB / 2 vCPU'),
                ('config-3072-2', lambda testenv: False,  '-'),

                #('config-1',     lambda testenv: False, '2 GiB / 1 vCPU'),
                #('config-2',     lambda testenv: False, '1 GiB / 1 vCPU'),
            ]),
            #Step.branch_repeat(2),
            Step.branch_repeat(10),
            my_test,
        ),
    )

if __name__ == '__main__':
    require_on_aqm_node()
    test()
