import sys
from .test_framework import TestCollection, require_on_aqm_node

class Testdef():
    def __init__(self, testenv):
        self.collection = None  # set by run_test
        self.dry_run = False  # if dry run no side effects should be caused
        self.testenv = testenv
        self.testbed = testenv.testbed  # shortcut to above
        self.level = 0

def run_test(folder=None, testenv=None, title=None, subtitle=None, steps=None, ask_confirmation=True):
    """
    Run a complete test using list of steps.

    See steps.py for example steps.
    """
    require_on_aqm_node()
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

    def walk(parent, steps, level=0):
        plot = True
        testdef.collection = parent

        # The last step should be the actual traffic generator
        if len(steps) == 1:
            if testdef.dry_run:
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
                    walk(parent, steps[1:], level)
                    continue

                child = parent
                if len(steps) > 1:
                    child = TestCollection(
                        title=step['title'],
                        titlelabel=step['titlelabel'],
                        folder=step['tag'],
                        parent=parent
                    )
                walk(child, steps[1:], level + 1)

                # the walk function have replaced our collection, so put it back
                testdef.collection = parent

    def get_root():
        return TestCollection(
            folder=folder,
            title=title,
            subtitle=subtitle,
        )

    testdef.dry_run = True
    walk(get_root(), steps)
    print('Estimated time: %d seconds for running %d (of %d) tests (average %g sec/test)\n' % (
        estimated_time, num_tests, num_tests_total, estimated_time / num_tests if num_tests > 0 else 0))

    run_test = not ask_confirmation
    if ask_confirmation:
        sys.stdout.write('Start test? [y/n] ')
        run_test = input().lower() == 'y'

    if run_test:
        testdef.dry_run = False
        walk(get_root(), steps)
