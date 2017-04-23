#!/usr/bin/env python3
#
# This script allows to run a traffic generator outside
# the testcase. E.g. on a manual setup!
#

import sys

from aqmt import MBIT, Testbed, TestEnv, processes, traffic
from aqmt.traffic import greedy, udp

def run_test(test_fn):

    testbed = Testbed()
    testenv = TestEnv(testbed, is_interactive=True)

    def run_traffic(traffic_fn, **kwargs):
        traffic_fn(
            dry_run=False,
            testbed=testbed,
            hint_fn=lambda hint: None,
            run_fn=testenv.run,
            **kwargs,
        )

    test_fn(run_traffic)

    sys.stdout.write('Press enter to stop traffic and cleanup ')
    input()

    processes.kill_known_pids()
    testenv.get_terminal().cleanup()

if __name__ == '__main__':
    def test(run_traffic):
        run_traffic(greedy, node='a')
        run_traffic(greedy, node='b')
        #run_traffic(udp, node='a', bitrate=150*MBIT, ect='nonect')  # ect1,nonect
        #run_traffic(udp, node='b', bitrate=150*MBIT, ect='ect1')  # ect1,nonect

    run_test(test)
