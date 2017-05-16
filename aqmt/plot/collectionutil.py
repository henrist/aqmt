"""
Module for utils for plotting collections

See treeutil.py for details of how the tree is structured
"""

from collections import OrderedDict
import math

from .common import PlotAxis
from . import treeutil


def get_tree_details(tree):
    """
    Returns a tuple containing:
    - number of leaf branches
    - number of tests
    - depth of the tree
    - number of x points
    """

    leafs = 0
    tests = 0
    depth = 0
    nodes = 0

    def traverse(branch, depthnow=0):
        nonlocal leafs, tests, depth, nodes

        if len(branch['children']) == 0:
            return

        f = branch['children'][0]

        if depthnow > depth:
            depth = depthnow

        # is this a set of tests?
        if len(f['children']) == 1 and 'testcase' in f['children'][0]:
            tests += len(branch['children'])
            leafs += 1
            nodes += len(branch['children'])

        # or is it a collection of collections
        else:
            for item in branch['children']:
                nodes += 1
                traverse(item, depthnow + 1)

    traverse(tree)
    return leafs, tests, depth, nodes - depth


def get_gap(tree):
    """
    Calculate the gap that a single test can fill in the graph.
    This tries to make the gap be visually the same for few/many tests.
    """
    _, _, _, n_nodes = get_tree_details(tree)
    return min(0.8, (n_nodes + 2) / 100)


def get_testcases(leaf):
    """
    Get list of testcases of a test collection

    Returns [(title, testcase_folder), ...]
    """
    return [(item['title'], item['children'][0]['testcase']) for item in leaf['children']]


def get_all_testcases_folders(tree):
    """
    Get a list of all testcase folders in a given tree
    """
    folders = []

    def parse_leaf(leaf, first_set, x):
        nonlocal folders
        folders += [item[1] for item in get_testcases(leaf)]  # originally list of (title, folder)

    treeutil.walk_leaf(tree, parse_leaf)
    return folders


def make_xtics(tree, xoffset, x_axis):
    """
    Generate a list of xtics

    This can be passed on to `set xtics add (<here>)` to add xtics
    to the graph.
    """

    arr = []

    minval, maxval, count = get_testmeta_min_max_count(tree, x_axis)

    numxtics = 10

    def frange(start, stop, step):
        i = start
        while i < stop:
            yield i
            i += step

    #print(minval, maxval)
    #step = ((maxval - minval) / numxtics)
    step = 20 # FIXME: this need to adopt to input
    minval = math.ceil(minval / step) * step
    maxval = math.floor(maxval / step) * step

    #print(minval, maxval)

    for x in frange(minval, maxval + step, step):
        arr.append('"%s" %g' % (
            round(x, 2),
            get_x_coordinate(tree, x, x_axis) + xoffset
        ))

    return ', '.join(arr)


def get_testmeta_min_max_count(leaf, x_axis):
    """
    This function expects all x label titles to be numeric value
    so we can calculate the minimum and maximum of them.
    """
    testcases = get_testcases(leaf)

    # logaritmic, we need to calculate the position
    minval = None
    maxval = None
    for title, testcase_folder in testcases:
        x = float(title)
        if minval is None or x < minval:
            minval = x
        if maxval is None or x > maxval:
            maxval = x

    return minval, maxval, len(testcases)


def get_x_coordinate(leaf, value, x_axis):
    """
    Calculates the linear x position that a value will
    be positioned"""

    minval, maxval, count = get_testmeta_min_max_count(leaf, x_axis)

    pos = float(value)
    if x_axis == PlotAxis.LOGARITHMIC:
        minval = math.log10(minval)
        maxval = math.log10(maxval)
        pos = math.log10(pos)

    return (pos - minval) / (maxval - minval) * (count - 1) if minval != maxval else 0


def merge_testcase_data_set_x(testcases, x_axis):
    """
    Takes in an array of data points for x axis for a single
    series and appends the x position of the data points.

    Each element in the array is an array itself:
    - xvalue (might be text if linear scale)
    - line (rest of line that is passed on)

    It also concatenates the array and return a final string
    """

    # for category axis we don't calculate anything
    if not PlotAxis.is_logarithmic(x_axis) and not PlotAxis.is_linear(x_axis):
        out = []
        i = 0
        for xval, line in testcases:
            out.append('%d %s' % (i, line))
            i += 1
        return ''.join(out)

    # calculate minimum and maximum value
    minval = None
    maxval = None
    for xval, line in testcases:
        x = float(xval)
        if minval is None or x < minval:
            minval = x
        if maxval is None or x > maxval:
            maxval = x

    if PlotAxis.is_logarithmic(x_axis):
        minval = math.log10(minval)
        maxval = math.log10(maxval)

    out = []
    for xval, line in testcases:
        pos = float(xval)
        if PlotAxis.is_logarithmic(x_axis):
            pos = math.log10(pos)
        x = (pos - minval) / (maxval - minval) * (len(testcases) - 1) if maxval != minval else 0
        out.append('%f %s' % (x, line))
    return ''.join(out)


def get_leaf_tests_stats(leaf, statsname):
    """
    Build data for a specific statistic from all testcases in a leaf

    The return value will be a list of tupples where first
    element is the title of this test and second element is
    the lines from the statistics with the title appended.
    """
    res = []
    for title, testcase_folder in get_testcases(leaf):
        added = False

        if callable(statsname):
            for line in statsname(testcase_folder).splitlines():
                if line.startswith('#'):
                    continue

                res.append((title, '"%s" %s\n' % (title, line)))
                added = True
                break  # only allow one line from each sample

        else:
            with open(testcase_folder + '/' + statsname, 'r') as f:
                for line in f:
                    if line.startswith('#'):
                        continue

                    res.append((title, '"%s" %s' % (title, line)))
                    added = True
                    break  # only allow one line from each sample

        if not added:
            res.append((title, '"%s"' % title))

    return res


def merge_testcase_data(leaf, statsname, x_axis):
    """
    statsname might be a function. It will be given the folder path
      of the test case and should return one line.
    """
    res = get_leaf_tests_stats(leaf, statsname)
    return merge_testcase_data_set_x(res, x_axis)


def merge_testcase_data_group(leaf, statsname, x_axis):
    """
    Similar to merge_testcase_data except it groups all data by first column

    There should only exist one data point in the files for each group
    """
    out = OrderedDict()

    i_file = 0
    for title, testcase_folder in get_testcases(leaf):
        with open(testcase_folder + '/' + statsname, 'r') as f:
            for line in f:
                if line.startswith('#') or line == '\n':
                    continue

                if line.startswith('"'):
                    i = line.index('"', 1)
                    group_by = line[1:i]
                else:
                    group_by = line.split()[0]

                if group_by not in out:
                    out[group_by] = [[title, '"%s"\n' % title]] * i_file

                out[group_by].append([title, '"%s" %s' % (title, line)])

        i_file += 1
        for key in out.keys():
            if len(out[key]) != i_file:
                out[key].append([title, '"%s"\n' % title])

    for key in out.keys():
        out[key] = merge_testcase_data_set_x(out[key], x_axis)

    return out


def get_xlabel(tree):
    """
    Get the label that are used for the x axis.

    This is taken from the titlelabel of a test collection.
    """
    xlabel = None

    def fn(leaf, first_set, x):
        nonlocal xlabel
        if xlabel is None and len(leaf['children']) > 0 and leaf['children'][0]['titlelabel'] != '':
            xlabel = leaf['children'][0]['titlelabel']

    treeutil.walk_leaf(tree, fn)
    return xlabel


def pt_generator():
    """
    Building point styles for use in plots.
    """
    pool = [1,2,3,8,10,12,14]
    i = 0
    tags = {}

    def get_val(tag):
        nonlocal i
        if tag not in tags:
            tags[tag] = pool[i % len(pool)]
            i += 1

        return tags[tag]

    return get_val
