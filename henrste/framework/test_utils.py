import sys
from framework.test_framework import TestCollection
from framework.plot import PlotAxis

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

def branch_sched(sched_list):
    def step(testdef):
        for sched in sched_list:
            tag = sched[0]
            title = sched[1]
            sched_fn = sched[2]

            sched_fn(testdef.testenv.testbed)

            yield {
                'tag': 'sched-%s' % tag,
                'title': title,
                'titlelabel': 'Scheduler',
            }
    return step

def branch_udp_rate(rate_list, title='UDP-rate: %d Mb/s'):
        def branch(testdef):
            for rate in rate_list:
                testdef.udp_rate = rate
                yield {
                    'tag': 'udp-rate-%s' % rate,
                    'title': title % rate,
                    'titlelabel': 'UDP Rate [Mb/s]',
                }
        return branch

def branch_repeat(num, title='Test %d'):
    def step(testdef):
        for i in range(num):
            yield {
                'tag': 'repeat-%d' % i,
                'title': title % i,
                'titlelabel': 'Test #',
            }
    return step

def branch_rtt(rtt_list, title='RTT: %d ms'):
    def step(testdef):
        for rtt in rtt_list:
            testdef.testenv.testbed.rtt_servera = rtt
            testdef.testenv.testbed.rtt_serverb = rtt
            yield {
                'tag': 'rtt-%d' % rtt,
                'title': title % rtt,
                'titlelabel': 'RTT',
            }
    return step

def branch_bitrate(bitrate_list, title='%d Mb/s'):
    def step(testdef):
        for bitrate in bitrate_list:
            testdef.testenv.testbed.bitrate = bitrate * MBIT
            yield {
                'tag': 'linkrate-%d' % bitrate,
                'title': title % bitrate,
                'titlelabel': 'Linkrate',
            }
    return step


def branch_runif(checks):
    def step(testdef):
        for tag, fn, title in checks:
            prev = testdef.testenv.skip_test
            testdef.testenv.skip_test = not fn(testdef.testenv)

            yield {
                'tag': 'runif-%s' % tag,
                'title': title,
                'titlelabel': 'Run if',
            }

            testdef.testenv.skip_test = prev
    return step

def step_skipif(fn):
    def step(testdef):
        prev = testdef.testenv.skip_test
        testdef.testenv.skip_test = fn(testdef.testenv)

        yield

        testdef.testenv.skip_test = prev

    return step

def plot_swap(offset=0):
    processed = False
    def step(testdef):
        nonlocal processed
        if not processed:
            level = testdef.level - 1 + offset
            testdef.swap_levels.append(level)
            processed = True
        yield
    return step

def plot_logarithmic(testdef):
    testdef.plot_x_axis = PlotAxis.LOGARITHMIC
    yield

def plot_linear(testdef):
    testdef.plot_x_axis = PlotAxis.LINEAR
    yield

class Testdef():
    def __init__(self, testenv):
        self.testenv = testenv
        self.testbed = testenv.testbed  # shortcut to above
        self.level = 0
        self.swap_levels = []
        self.plot_x_axis = PlotAxis.CATEGORY

    def gen_swap_levels(self, level):
        l = []
        for item in self.swap_levels:
            n = item - level
            if n >= 0:
                l.append(n)
        return l

def run_test(folder=None, testenv=None, title=None, subtitle=None, steps=None, swap_levels=[], ask_confirmation=True):
    testdef = Testdef(testenv)

    # Save testdef to testenv so we can pull it from the test case we are running.
    # We use this to hold internal parameters.
    testenv.testdef = testdef

    num_tests = 0
    estimated_time = 0
    num_tests_total = 0
    def get_metadata(testcollection, testenv):
        nonlocal estimated_time, num_tests, num_tests_total
        meta = testcollection.get_metadata(testenv)
        estimated_time += meta['estimated_time'] if meta['will_test'] else 0
        num_tests += 1 if meta['will_test'] else 0
        num_tests_total += 1

    def walk(parent, steps, only_meta=False, level=0, parent_step=None):
        plot = True

        # The last step should be the actual traffic generator
        if len(steps) == 1:
            if only_meta:
                get_metadata(parent, testenv)
            else:
                parent.run_test(
                    test_fn=steps[0],
                    testenv=testenv
                )

        else:
            # Each step should be a generator, yielding metadata for new branches.
            # If the generator yields nothing, we jump to next level.
            testdef.level = level
            for step in steps[0](testdef):
                if not step:
                    walk(parent, steps[1:], only_meta, level, parent_step)
                    plot = False
                    continue

                child = parent
                if len(steps) > 1:
                    child = TestCollection(
                        title=step['title'],
                        titlelabel=step['titlelabel'],
                        folder=step['tag'],
                        parent=parent
                    )
                walk(child, steps[1:], only_meta, level + 1, step)

        if plot and not only_meta:
            parent.plot(
                utilization_tags=True,
                utilization_queues=False,
                swap_levels=testdef.gen_swap_levels(level),
                x_axis=testdef.plot_x_axis,
            )

    def get_root():
        return TestCollection(
            folder=folder,
            title=title,
            subtitle=subtitle,
        )

    walk(get_root(), steps, only_meta=True)
    print('Estimated time: %d seconds for running %d (of %d) tests (average %g sec/test)\n' % (
        estimated_time, num_tests, num_tests_total, estimated_time / num_tests if num_tests > 0 else 0))

    run_test = not ask_confirmation
    if ask_confirmation:
        sys.stdout.write('Start test? [y/n] ')
        run_test = input().lower() == 'y'

    if run_test:
        walk(get_root(), steps)
