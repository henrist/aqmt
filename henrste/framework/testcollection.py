"""
This module contains the test collection logic
"""

import os
import time
import sys

from . import logger
from .plot import Plot
from . import processes
from .testcase import TestCase
from .testenv import remove_hint, save_hint_to_folder

class TestCollection:
    """Organizes tests in collections and stores metadata used to automatically plot

    Test hierarchy looks like (from bottom up):
    - collection of a single test
    - collection of collections, and so on
    """

    def __init__(self, folder, title=None, subtitle=None, titlelabel=None, parent=None):
        if parent:
            self.folder = parent.folder + '/' + folder
            parent.check_and_add_tag(folder)
        else:
            self.folder = folder

        self.tags_used = []  # to make sure we have unique tags as children

        self.test = None
        self.collections = []

        self.parent = parent
        self.parent_called = False

        self.hints_initialized = False  # defer initialization of hints till we have data
        self.title = title
        self.subtitle = subtitle
        self.titlelabel = titlelabel

    def check_and_add_tag(self, tag):
        """
        This ensures we don't have duplicate tags in the collection
        """
        if tag in self.tags_used:
            raise Exception("Tag must be unique inside same collection (tag: %s)" % tag)

        self.tags_used.append(tag)

    def add_child(self, child_folder):
        """
        Add a child of this collection.

        It can be another collection (then this is called by the child
        collection itself), or a single test.

        The start of call chain for this is a test that has data.
        If no tests with data are inside this collection, it will
        never be visible in folder structure.
        """
        if not self.hints_initialized:
            self.hints_initialized = True
            remove_hint(self.folder)
            save_hint_to_folder(self.folder, 'type collection')

            if self.title is not None:
                save_hint_to_folder(self.folder, 'title %s' % self.title)

            if self.subtitle is not None:
                save_hint_to_folder(self.folder, 'subtitle %s' % self.subtitle)

            if self.titlelabel is not None:
                save_hint_to_folder(self.folder, 'titlelabel %s' % self.titlelabel)

        save_hint_to_folder(self.folder, 'sub %s' % child_folder)

        if self.parent and not self.parent_called:
            self.parent_called = True
            self.parent.collections.append(self)
            self.parent.add_child(os.path.basename(self.folder))

    def run_test(self, test_fn, testenv):
        """
        Run a single test (the smallest possible test)

        test_fn: Method that generates test data
        """

        if self.test:
            raise Exception("A collection cannot contain multiple tests")

        test_folder = 'test'

        self.test = TestCase(testenv=testenv, folder=self.folder + '/' + test_folder)
        self.test.log_header()

        if not self.test.should_skip():
            self.test.run(test_fn)

        if (self.test.data_collected or self.test.already_exists) and not testenv.dry_run:
            if testenv.reanalyze or not self.test.already_exists:
                start = time.time()
                self.test.analyze()
                logger.info('Analyzed test (%.2f s)' % (time.time()-start))

            if testenv.reanalyze or testenv.replot or not self.test.already_exists:
                start = time.time()

                p = Plot()
                p.plot_flow(self.test.test_folder)

                logger.info('Plotted test (%.2f s)' % (time.time()-start))

            self.add_child(test_folder)

        elif self.test.already_exists:
            self.add_child(test_folder)

        # if we have received a SIGTERM we will terminate TA but allow the plotting
        if processes.is_exiting:
            processes.kill_known_pids()
            testenv.get_terminal().cleanup()
            sys.exit()

    def get_metadata(self, testenv):
        """
        Instead of running the test, this method can be called
        to generate various metedata without actually running the test.
        """
        test = TestCase(testenv=testenv, folder=self.folder + '/test')
        return {
            'estimated_time': test.calc_estimated_run_time(),
            'will_test': not test.should_skip(),
        }
