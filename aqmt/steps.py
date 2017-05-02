"""
This module contains predefined steps that can be applied
when composing a test hiearchy. Feel free to write your own
instead of using these.

A step is required to yield (minimum one time) in two different ways:

- Yield nothing: This does not cause a branch in the test hierarchy.

- Yield object: Should be an object with the following properties, and
  will cause a new branch with these properties:
  - tag
  - title
  - titlelabel
"""

import os.path

from .plot import generate_hierarchy_data_from_folder, \
                  plot_folder_flows, plot_folder_compare, \
                  reorder_levels
from .testcollection import build_html_index

MBIT = 1000*1000


def branch_sched(sched_list, titlelabel='Scheduler'):
    def step(testdef):
        for tag, title, sched_name, sched_params in sched_list:
            testdef.testenv.testbed.aqm(sched_name, sched_params)
            testdef.sched_tag = tag  # to allow substeps to filter it

            yield {
                'tag': 'sched-%s' % tag,
                'title': title,
                'titlelabel': titlelabel,
            }
    return step


def branch_custom(list, fn_testdef, fn_tag, fn_title, titlelabel=''):
    def step(testdef):
        for item in list:
            fn_testdef(testdef, item)
            yield {
                'tag': 'custom-%s' % fn_tag(item),
                'title': fn_title(item),
                'titlelabel': titlelabel,
            }
    return step


def branch_define_udp_rate(rate_list, title='%g', titlelabel='UDP Rate [Mb/s]'):
    """
    This method don't actually change the setup, it only sets a variable
    that can be used when running the actual test.
    """
    def branch(testdef):
        for rate in rate_list:
            testdef.udp_rate = rate
            yield {
                'tag': 'udp-rate-%s' % rate,
                'title': title % rate,
                'titlelabel': titlelabel,
            }
    return branch


def branch_repeat(num, title='%d', titlelabel='Test #'):
    def step(testdef):
        for i in range(num):
            yield {
                'tag': 'repeat-%d' % i,
                'title': title % (i + 1),
                'titlelabel': titlelabel,
            }
    return step


def branch_rtt(rtt_list, title='%d', titlelabel='RTT'):
    def step(testdef):
        for rtt in rtt_list:
            testdef.testenv.testbed.rtt_servera = rtt
            testdef.testenv.testbed.rtt_serverb = rtt
            yield {
                'tag': 'rtt-%d' % rtt,
                'title': title % rtt,
                'titlelabel': titlelabel,
            }
    return step


def branch_bitrate(bitrate_list, title='%d', titlelabel='Linkrate [Mb/s]'):
    def step(testdef):
        for bitrate in bitrate_list:
            testdef.testenv.testbed.bitrate = bitrate * MBIT
            yield {
                'tag': 'linkrate-%d' % bitrate,
                'title': title % bitrate,
                'titlelabel': titlelabel,
            }
    return step


def branch_runif(checks, titlelabel='Run if'):
    def step(testdef):
        for tag, fn, title in checks:
            prev = testdef.testenv.skip_test
            testdef.testenv.skip_test = not fn(testdef.testenv)

            yield {
                'tag': 'runif-%s' % tag,
                'title': title,
                'titlelabel': titlelabel,
            }

            testdef.testenv.skip_test = prev
    return step


def skipif(fn):
    def step(testdef):
        prev = testdef.testenv.skip_test
        testdef.testenv.skip_test = fn(testdef.testenv)

        yield

        testdef.testenv.skip_test = prev

    return step


def add_pre_hook(fn):
    """
    Add a pre hook to the testcase. Passed to TestCase's run method.
    """
    def step(testdef):
        old_hook = testdef.pre_hook
        def new_hook(*args, **kwargs):
            if callable(old_hook):
                old_hook(*args, **kwargs)
            fn(*args, **kwargs)
        testdef.pre_hook = new_hook
        yield
        testdef.pre_hook = old_hook
    return step


def add_post_hook(fn):
    """
    Add a post hook to the testcase. Passed to TestCase's run method.
    """
    def step(testdef):
        old_hook = testdef.post_hook
        def new_hook(*args, **kwargs):
            if callable(old_hook):
                old_hook(*args, **kwargs)
            fn(*args, **kwargs)
        testdef.post_hook = new_hook
        yield
        testdef.post_hook = old_hook
    return step


def plot_compare(**plot_args):
    def step(testdef):
        yield
        if not testdef.dry_run and os.path.isdir(testdef.collection.folder):
            plot_folder_compare(testdef.collection.folder, **plot_args)
    return step


def plot_flows(**plot_args):
    def step(testdef):
        yield
        if not testdef.dry_run and os.path.isdir(testdef.collection.folder):
            plot_folder_flows(testdef.collection.folder, **plot_args)
    return step


def plot_test(name='analysis', **plot_args):
    """
    Define a named plot on the test.

    plot_args is sent to plot_test()
    """
    def step(testdef):
        yield
        testdef.test_plots[name] = plot_args
    return step


def html_index(level_order=None):
    def step(testdef):
        yield

        if not testdef.dry_run and os.path.isdir(testdef.collection.folder):
            tree = reorder_levels(
                generate_hierarchy_data_from_folder(testdef.collection.folder),
                level_order=level_order,
            )

            out = build_html_index(tree, testdef.collection.folder)

            with open(testdef.collection.folder + '/index.html', 'w') as f:
                f.write(out)

    return step