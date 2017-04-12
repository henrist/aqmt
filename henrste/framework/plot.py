#!/usr/bin/env python3
import argparse
from plumbum import local
import math
import os.path
import os
import re
import sys
from pprint import pprint
from collections import OrderedDict

class Colors:
    BLUE = "#001E90FF"
    LILAC = "#007570B3"
    RED = "#00FF0000"
    BLACK = "#00333333"
    GREEN = "#0066A61E"
    GRAY = "#00666666"

    CC_DCTCP = BLUE
    CC_CUBIC = RED
    CC_RENO = RED
    CC_CUBIC_ECN = BLACK

    L4S = BLUE
    CLASSIC = RED
    AGGR = GREEN

    CLASS_NOECT = '#00E7298A'
    CLASS_ECT0 = '#00333333'
    CLASS_ECT1 = '#00666666'
    CLASS_UNKNOWN_UDP = GRAY
    UNKNOWN = "#00D2691E"

    DROPS_CLASSIC = RED
    DROPS_L4S = BLUE
    MARKS_L4S = GRAY

    title_map = (
        ('cubic-ecn', CC_CUBIC_ECN),
        ('ecn-cubic', CC_CUBIC_ECN),
        ('cubic', CC_CUBIC),
        ('dctcp', CC_DCTCP),
        ('reno', CC_RENO),
        ('ect(1)', CLASS_ECT1),
        ('ect(0)', CLASS_ECT0),
        ('udp=non ect', CLASS_NOECT),
        ('udp', CLASS_UNKNOWN_UDP),
        ('other', UNKNOWN),
    )

    @staticmethod
    def get_from_tagname(title):
        title = title.lower()

        for key, value in Colors.title_map:
            if key in title:
                return value

        return Colors.UNKNOWN

class PlotAxis():
    """Different ways to display x axis in each test"""
    LOGARITHMIC='log'
    LINEAR='linear'
    CATEGORY='category'

class TreeUtil():

    @staticmethod
    def get_depth_sizes(testmeta):
        """Calculate the number of nodes at each tree level"""
        depths = {}

        def check_node(item, x, depth):
            if depth not in depths:
                depths[depth] = 0
            depths[depth] += 1

        TreeUtil.walk_tree(testmeta, check_node)
        return depths

    @staticmethod
    def get_num_testcases(testmeta):
        """Returns a tuple of number of sets, tests and depth"""

        sets = 0
        tests = 0
        depth = 0
        nodes = 0

        def traverse(testmeta, depthnow=0):
            nonlocal sets, tests, depth, nodes

            if len(testmeta['children']) == 0:
                return

            f = testmeta['children'][0]

            if depthnow > depth:
                depth = depthnow

            # is this a set of tests?
            if len(f['children']) == 1 and 'testcase' in f['children'][0]:
                tests += len(testmeta['children'])
                sets += 1
                nodes += len(testmeta['children'])

            # or is it a collection of collections
            else:
                for item in testmeta['children']:
                    nodes += 1
                    traverse(item, depthnow + 1)

        traverse(testmeta)
        return (sets, tests, depth, nodes - depth)

    @staticmethod
    def get_testcases(testmeta):
        """Get list of testcases of a test collection

        Returns [(title, testcase_folder), ...]
        """
        return [(item['title'], item['children'][0]['testcase']) for item in testmeta['children']]

    @staticmethod
    def walk_leaf(testmeta, fn):
        """Walks the tree and calls fn for every leaf collection (collection of tests)

        The arguments to fn:
        - object: this subtree
        - bool: true if first leaf node in tree
        - number: the offset of this leaf node
        """

        first_set = True
        x = 0

        def walk(testmeta):
            nonlocal first_set, x

            if len(testmeta['children']) == 0:
                return

            f = testmeta['children'][0]

            # is this a set of tests?
            if len(f['children']) == 1 and 'testcase' in f['children'][0]:
                fn(testmeta, first_set, x)
                first_set = False
                x += len(testmeta['children'])

            # or is it a collection of collections
            else:
                for item in testmeta['children']:
                    walk(item)

            x += 1

        walk(testmeta)

    @staticmethod
    def walk_tree_reverse(testmeta, fn):
        """Walks the tree and calls fn for every subtree (collection) in reverse order

        Excludes the leaf nodes (collection of tests)

        The arguments to fn:
        - object: the subtree
        - number: ?
        - number: ?
        - number: ?
        """
        x = 0

        def walk(testmeta, depth):
            nonlocal x

            if len(testmeta['children']) == 0:
                return

            f = testmeta['children'][0]

            # is this a collection of tests?
            if len(f['children']) == 1 and 'testcase' in f['children'][0]:
                x += len(testmeta['children'])

            # or else it is a collection of collections
            else:
                for item in testmeta['children']:
                    y = x
                    walk(item, depth + 1)
                    fn(item, y, depth, x - y)

            x += 1

        walk(testmeta, 0)

    @staticmethod
    def walk_tree(testmeta, fn, include_test_node=False):
        """Walks the tree and calls fn for every tree node (collection)

        Includes the tree node that is a collection of tests if
        the parameter is given.

        The arguments to fn:
        - object: tree node (collection)
        - number: the offset of node
        - number: depth of this node
        """
        x = 0

        def walk(testmeta, depth):
            nonlocal x

            if len(testmeta['children']) == 0:
                return

            f = testmeta['children'][0]

            if include_test_node:
                # is this a set of tests?
                if 'testcase' in f:
                    x += len(testmeta['children'])

                # or is it a list of sets
                else:
                    for item in testmeta['children']:
                        fn(item, x, depth)
                        walk(item, depth + 1)
            else:
                # is this a collection of tests?
                if len(f['children']) == 1 and 'testcase' in f['children'][0]:
                    x += len(testmeta['children'])

                # or else it is a collection of collections
                else:
                    for item in testmeta['children']:
                        fn(item, x, depth)
                        walk(item, depth + 1)

            x += 1

        walk(testmeta, 0)

    @staticmethod
    def swap_levels(spec, level=0):
        """Swap vertical position of elements in the tree

        This can be called to change the way nodes are grouped
        to columns in the plots
        """

        if level > 0:
            def walk(testmeta, depth):
                if len(testmeta['children']) == 0:
                    return

                # is this a set of tests?
                if 'testcase' in testmeta['children'][0]:
                    return

                for index, item in enumerate(testmeta['children']):
                    if depth + 1 == level:
                        testmeta['children'][index] = TreeUtil.swap_levels(item)
                    else:
                        walk(item, depth + 1)

            walk(spec, 0)
            return spec

        titles = []
        def check_level(item, x, depth):
            nonlocal titles
            if depth == 1 and item['title'] not in titles:
                titles.append(item['title'])
        TreeUtil.walk_tree(spec, check_level, include_test_node=True)

        if len(titles) == 0:
            return spec

        new_children = OrderedDict()
        parent = None

        def build_swap(item, x, depth):
            nonlocal parent, new_children
            if depth == 0:
                parent = item
            elif depth == 1:
                parentcopy = dict(parent)
                if item['title'] in new_children:
                    new_children[item['title']]['children'].append(parentcopy)
                else:
                    childcopy = dict(item)
                    childcopy['children'] = [parentcopy]
                    new_children[item['title']] = childcopy

                parentcopy['children'] = item['children']

        TreeUtil.walk_tree(spec, build_swap, include_test_node=True)

        spec['children'] = [val for key, val in new_children.items()]
        return spec


class CollectionUtil():

    @staticmethod
    def make_xtics(testmeta, xoffset, x_axis):
        """Generate a list of xtics

        This can be passed on to `set xtics add (<here>)` to add xtics
        to the graph.
        """

        arr = []

        minval, maxval, count = CollectionUtil.get_testmeta_min_max_count(testmeta, x_axis)

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
                CollectionUtil.get_x_coordinate(testmeta, x, x_axis) + xoffset
            ))

        return ', '.join(arr)

    @staticmethod
    def line_at_x_offset(xoffset, value_at_x, testmeta, x_axis):
        xpos = CollectionUtil.get_x_coordinate(testmeta, value_at_x, x_axis)

        return """
            set style line 100 lt 1 lc rgb 'red' lw .5 dt 7
            set arrow from first """ + str(xpos+xoffset) + """, graph 0 to first """ + str(xpos+xoffset) + """, graph 1 nohead ls 100 back
        """

    @staticmethod
    def get_testmeta_min_max_count(testmeta, x_axis):
        """
        This function expects all x label titles to be numeric value
        so we can calculate the minimum and maximum of them.
        """
        testcases = TreeUtil.get_testcases(testmeta)

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

    @staticmethod
    def get_x_coordinate(testmeta, value, x_axis):
        """Calculates the linear x position that a value will
        be positioned"""

        minval, maxval, count = CollectionUtil.get_testmeta_min_max_count(testmeta, x_axis)

        pos = float(value)
        if x_axis == PlotAxis.LOGARITHMIC:
            minval = math.log10(minval)
            maxval = math.log10(maxval)
            pos = math.log10(pos)

        return (pos - minval) / (maxval - minval) * (count - 1) if minval != maxval else 0

    @staticmethod
    def merge_testcase_data_set_x(testcases, x_axis):
        """Takes in an array of data points for x axis for a single
        series and appends the x position of the data points.

        Each element in the array is an array itself:
        - xvalue (might be text if linear scale)
        - line (rest of line that is passed on)

        It also concatenates the array and return a final string
        """

        # for category axis we don't calculate anything
        if x_axis == PlotAxis.CATEGORY:
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

        if x_axis == PlotAxis.LOGARITHMIC:
            minval = math.log10(minval)
            maxval = math.log10(maxval)

        out = []
        for xval, line in testcases:
            pos = float(xval)
            if x_axis == PlotAxis.LOGARITHMIC:
                pos = math.log10(pos)
            x = (pos - minval) / (maxval - minval) * (len(testcases) - 1) if maxval != minval else 0
            out.append('%f %s' % (x, line))
        return ''.join(out)

    @staticmethod
    def get_testcase_data(testmeta, statsname):

        res = []
        for title, testcase_folder in TreeUtil.get_testcases(testmeta):
            added = False
            with open(testcase_folder + '/' + statsname, 'r') as f:
                for line in f:
                    if line.startswith('#'):
                        continue

                    res.append([title, '"%s" %s' % (title, line)])
                    added = True
                    break  # only allow one line from each sample

            if not added:
                res.append([title, '"%s"' % title])

        return res

    @staticmethod
    def merge_testcase_data(testmeta, statsname, x_axis):
        res = CollectionUtil.get_testcase_data(testmeta, statsname)
        return CollectionUtil.merge_testcase_data_set_x(res, x_axis)

    @staticmethod
    def merge_testcase_data_group(testmeta, statsname, x_axis):
        """Similar to merge_testcase_data except it groups all data by first column

        There should only exist one data point in the files for each group
        """
        out = OrderedDict()

        i_file = 0
        for title, testcase_folder in TreeUtil.get_testcases(testmeta):
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
            out[key] = CollectionUtil.merge_testcase_data_set_x(out[key], x_axis)

        return out

    @staticmethod
    def get_xlabel(testmeta):
        xlabel = None
        def fn(testmeta, first_set, x):
            nonlocal xlabel
            if xlabel == None and len(testmeta['children']) > 0 and testmeta['children'][0]['titlelabel'] != '':
                xlabel = testmeta['children'][0]['titlelabel']

        TreeUtil.walk_leaf(testmeta, fn)
        return xlabel

class CollectionPlot():
    """Plot a collection of test cases

    It is assumed that all leafs are of the same structure,
    but not necessary same amount of test cases inside
    a leaf
    """

    def __init__(self, output_file, testmeta, x_axis=PlotAxis.CATEGORY):
        self.plotutils = Plot()
        self.gpi = ''
        self.testmeta = testmeta
        self.output_file = output_file

        self.y_is_logarithmic = False  # TODO: should be able to configure this
        self.x_axis = x_axis
        self.custom_xtics = self.x_axis != PlotAxis.CATEGORY
        self.lines_at_x_offset = []  # [100, 115, 130]

        self.n_sets, self.n_tests, self.n_depth, self.n_nodes = TreeUtil.get_num_testcases(testmeta)

        self.tmargin_base = 1 * self.n_depth + 2
        if 'subtitle' in self.testmeta and self.testmeta['subtitle']:
            self.tmargin_base += .8

        self.depth_sizes = TreeUtil.get_depth_sizes(testmeta)

    def plot_labels(self, testmeta, x, depth, width):
        """Labels are text located above the graphs"""
        fontsize = fontsize = max(5, min(9, 10 - self.depth_sizes[depth] / 4.5))

        centering = False
        x_offset = x + (width - 2) / 2 if centering else x

        self.gpi += """
            set label \"""" + testmeta['title'] + """\" at first """ + str(x_offset) + """, graph """ + str(1.05 + 0.06 * (self.n_depth - depth - 1)) + """ font 'Times-Roman,""" + str(fontsize) + """pt' tc rgb 'black' left"""

    def plot_utilization_queues(self):
        """Plot graph of utilization for total, ECN and non-ECN flows"""
        self.gpi += self.common_header()
        self.gpi += """

            # utilization
            set style line 100 lt 1 lc rgb 'black' lw 1.5 dt 3
            set arrow 100 from graph 0, first 100 to graph 1, first 100 nohead ls 100 back

            set ylabel "Utilization per queue [%]\\n{/Times:Italic=10 (p_1, mean, p_{99})}"
            """

        if self.custom_xtics:
            self.gpi += """
                # add xtics below, the empty list resets the tics
                set xtics ()
                """

        plot = ''
        titles_used = []
        def data_util(testmeta, is_first_set, x):
            nonlocal plot, titles_used

            xtics = ":xtic(2)"
            if self.custom_xtics:
                xtics = ""
                self.gpi += """
                    set xtics add (""" + CollectionUtil.make_xtics(testmeta, x, self.x_axis) + """)
                    """

            for xoffset in self.lines_at_x_offset:
                self.gpi += CollectionUtil.line_at_x_offset(x, xoffset, testmeta, self.x_axis)

            self.gpi += """
                $data_util_total""" + str(x) + """ << EOD
                """ + CollectionUtil.merge_testcase_data(testmeta, 'derived/util_total_stats', self.x_axis) + """
                EOD
                $data_util_ecn""" + str(x) + """ << EOD
                """ + CollectionUtil.merge_testcase_data(testmeta, 'derived/util_ecn_stats', self.x_axis) + """
                EOD
                $data_util_nonecn""" + str(x) + """ << EOD
                """ + CollectionUtil.merge_testcase_data(testmeta, 'derived/util_nonecn_stats', self.x_axis) + """
                EOD"""

            # total
            plot += "$data_util_total" + str(x) + "  using ($1+" + str(x) + "+0.0):3:10:6" + xtics + "       with yerrorbars ls 1 pointtype 7 pointsize 0.4 lc rgb '" + Colors.AGGR + "' lw 1.5 title '" + ('Total utilization' if is_first_set else '') + "', \\\n"
            #plot += "''                              using ($1+" + str(x) + "+0.0):7  with points  ls 1 pointtype 1 pointsize 0.4        title '', \\\n"
            #plot += "''                              using ($1+" + str(x) + "+0.0):9  with points  ls 1 pointtype 1 pointsize 0.4        title '', \\\n"
            plot += "''                              using ($1+" + str(x) + "+0.0):3  with lines lc rgb 'gray'         title '', \\\n" # gray lines total, ecn, nonecn

            # ecn
            plot += "$data_util_ecn" + str(x) + "  using ($1+" + str(x) + "+0.1):3:10:6    with yerrorbars ls 2 pointtype 7 pointsize 0.4 lc rgb '" + Colors.L4S + "' lw 1.5 title '" + ('ECN utilization' if is_first_set else '') + "', \\\n"
            #plot += "''                            using ($1+" + str(x) + "+0.1):7   with points  ls 2 pointtype 1 pointsize 0.4        title '', \\\n"
            #plot += "''                            using ($1+" + str(x) + "+0.1):9  with points  ls 2 pointtype 1 pointsize 0.4        title '', \\\n"
            plot += "''                            using ($1+" + str(x) + "+0.1):3  with lines lc rgb 'gray'         title '', \\\n" # gray lines total, ecn, nonecn

            # nonecn
            plot += "$data_util_nonecn" + str(x) + "  using ($1+" + str(x) + "+0.2):3:10:5  with yerrorbars ls 3 pointtype 7 pointsize 0.4 lc rgb '" + Colors.CLASSIC + "' lw 1.5 title '" + ('Non-ECN utilization' if is_first_set else '') + "', \\\n"
            #plot += "''                               using ($1+" + str(x) + "+0.2):7  with points  ls 3 pointtype 1 pointsize 0.4        title '', \\\n"
            #plot += "''                               using ($1+" + str(x) + "+0.2):9  with points  ls 3 pointtype 1 pointsize 0.4        title '', \\\n"
            plot += "''                               using ($1+" + str(x) + "+0.2):3  with lines lc rgb 'gray'         title '', \\\n" # gray lines total, ecn, nonecn

        TreeUtil.walk_leaf(self.testmeta, data_util)
        self.gpi += """
            plot \\
            """ + plot + """

            unset arrow 100"""

    def plot_utilization_tags(self):
        self.gpi += self.common_header()
        self.gpi += """

            # utilization of tags
            set style line 100 lt 1 lc rgb 'black' lw 1.5 dt 3
            set arrow 100 from graph 0, first 100 to graph 1, first 100 nohead ls 100 back

            set ylabel "Utilization of classified traffic [%]\\n{/Times:Italic=10 (p_{25}, mean, p_{75})}"
            """

        if self.custom_xtics:
            self.gpi += """
                # add xtics below, the empty list resets the tics
                set xtics ()
                """

        plot = ''
        plot_lines = ''
        titles_used = []
        def data_util_tags(testmeta, is_first_set, x):
            nonlocal plot, plot_lines, titles_used

            xtics = ":xtic(2)"
            if self.custom_xtics:
                xtics = ""
                self.gpi += """
                    set xtics add (""" + CollectionUtil.make_xtics(testmeta, x, self.x_axis) + """)
                    """

            for xoffset in self.lines_at_x_offset:
                self.gpi += CollectionUtil.line_at_x_offset(x, xoffset, testmeta, self.x_axis)

            self.gpi += """
                $dataUtil""" + str(x) + """ << EOD
                """ + CollectionUtil.merge_testcase_data(testmeta, 'derived/util_total_stats', self.x_axis) + """
                EOD"""

            # total
            plot += "$dataUtil" + str(x) + "  using ($1+" + str(x) + "+0.0):3:9:7" + xtics + "       with yerrorbars ls 1 pointtype 7 pointsize 0.4 lc rgb '" + Colors.AGGR + "' lw 1.5 title '" + ('Total utilization' if is_first_set else '') + "', \\\n"
            plot_lines += "$dataUtil" + str(x) + "  using ($1+" + str(x) + "+0.0):3  with lines lc rgb 'gray'         title '', \\\n"

            tagged_flows = CollectionUtil.merge_testcase_data_group(testmeta, 'derived/util_tagged_stats', self.x_axis)
            x_distance = .4 / len(tagged_flows)

            for i, (tagname, data) in enumerate(tagged_flows.items()):
                self.gpi += """
                    $dataUtil""" + str(x) + "_" + str(i) + """ << EOD
                    """ + data + """
                    EOD"""

                if tagname in titles_used:
                    title = ''
                else:
                    titles_used.append(tagname)
                    title = tagname
                ls = str(titles_used.index(tagname) + 4)

                plot += "$dataUtil" + str(x) + "_" + str(i) + "  using ($1+" + str(x+((i+1) * x_distance)) + "):($6*100):($7*100):($6*100)       with yerrorbars ls 1 pointtype 7 pointsize 0.4 lc rgb '" + Colors.get_from_tagname(tagname) + "' lw 1.5 title '" + title + "', \\\n"
                plot_lines += "$dataUtil" + str(x) + "_" + str(i) + "  using ($1+" + str(x+((i+1) * x_distance)) + "):($6*100) with lines lc rgb 'gray' title '', \\\n"

        TreeUtil.walk_leaf(self.testmeta, data_util_tags)

        self.gpi += """
            set tmargin """ + str(self.tmargin_base + 1.3 * (len(titles_used)+1) / 4 - 1) + """

            plot \\
            """ + plot + plot_lines + """

            unset arrow 100"""

    def plot_queueing_delay(self):
        self.gpi += self.common_header()
        self.gpi += """

            # queueing delay
            #set yrange [""" + ('1' if self.y_is_logarithmic else '0') + """:*]
            set yrange [0:*]
            unset logscale y

            set ylabel "Queueing delay per queue [ms]\\n{/Times:Italic=10 (p_1, p_{25}, mean, p_{75}, p_{99})}"
            #set xtic offset first .1
            """

        if self.custom_xtics:
            self.gpi += """
                # add xtics below, the empty list resets the tics
                set xtics ()
                """

        plot = ''
        def data_rate(testmeta, is_first_set, x):
            nonlocal plot

            xtics = ":xtic(2)"
            if self.custom_xtics:
                xtics = ""
                self.gpi += """
                    set xtics add (""" + CollectionUtil.make_xtics(testmeta, x, self.x_axis) + """)
                    """

            for xoffset in self.lines_at_x_offset:
                self.gpi += CollectionUtil.line_at_x_offset(x, xoffset, testmeta, self.x_axis)

            self.gpi += """
                $data_qs_ecn_stats""" + str(x) + """ << EOD
                """ + CollectionUtil.merge_testcase_data(testmeta, 'derived/qs_ecn_stats', self.x_axis) + """
                EOD
                $data_qs_nonecn_stats""" + str(x) + """ << EOD
                """ + CollectionUtil.merge_testcase_data(testmeta, 'derived/qs_nonecn_stats', self.x_axis) + """
                EOD"""

            ls_l4s = "ls 1 lc rgb '" + Colors.L4S + "'"
            ls_classic = "ls 1 lc rgb '" + Colors.CLASSIC + "'"

            plot += "$data_qs_ecn_stats" + str(x) + "    using ($1+" + str(x) + "+0.05):3:7:9" + xtics + "   with yerrorbars " + ls_l4s + " lw 1.5 pointtype 7 pointsize 0.4            title '" + ('ECN packets' if is_first_set else '') + "', \\\n"
            plot += "''                                  using ($1+" + str(x) + "+0.05):6  with points  " + ls_l4s + " pointtype 1 pointsize 0.4        title '', \\\n"
            plot += "''                                  using ($1+" + str(x) + "+0.05):10  with points  " + ls_l4s + " pointtype 1 pointsize 0.4        title '', \\\n"
            plot += "$data_qs_nonecn_stats" + str(x) + " using ($1+" + str(x) + "+0.15):3:7:9  with yerrorbars " + ls_classic + " lw 1.5 pointtype 7 pointsize 0.4           title '" + ('Non-ECN packets' if is_first_set else '') + "', \\\n"
            plot += "''                                  using ($1+" + str(x) + "+0.15):6  with points " + ls_classic + " pointtype 1 pointsize 0.4        title '', \\\n"
            plot += "''                                  using ($1+" + str(x) + "+0.15):10  with points " + ls_classic + " pointtype 1 pointsize 0.4        title '', \\\n"

            plot += "$data_qs_ecn_stats" + str(x) + "    using ($1+" + str(x) + "+0.05):3  with lines lc rgb 'gray'         title '', \\\n"
            plot += "$data_qs_nonecn_stats" + str(x) + " using ($1+" + str(x) + "+0.15):3  with lines lc rgb 'gray'         title '', \\\n"

        TreeUtil.walk_leaf(self.testmeta, data_rate)
        self.gpi += """
            plot \\
            """ + plot

    def plot_drops_marks(self):
        self.gpi += self.common_header()
        self.gpi += """

            # drops and marks
            set ylabel "Drop/marks per queue [%]\\n{/Times=10 (of total traffic in the queue)}\\n{/Times:Italic=10 (p_1, p_{25}, mean, p_{75}, p_{99})}"
            set xtic offset first 0
            """

        if self.custom_xtics:
            self.gpi += """
                # add xtics below, the empty list resets the tics
                set xtics ()
                """

        # show xlabel at bottom of the multiplot
        xlabel = CollectionUtil.get_xlabel(self.testmeta)
        if xlabel != None:
            self.gpi += """
                set xlabel '""" + xlabel + """'"""

        plot = ''
        def data_drops(testmeta, is_first_set, x):
            nonlocal plot

            xtics = ":xtic(2)"
            if self.custom_xtics:
                xtics = ""
                self.gpi += """
                    set xtics add (""" + CollectionUtil.make_xtics(testmeta, x, self.x_axis) + """)
                    """

            for xoffset in self.lines_at_x_offset:
                self.gpi += CollectionUtil.line_at_x_offset(x, xoffset, testmeta, self.x_axis)

            self.gpi += """
                $data_d_percent_ecn_stats""" + str(x) + """ << EOD
                """ + CollectionUtil.merge_testcase_data(testmeta, 'derived/d_percent_ecn_stats', self.x_axis) + """
                EOD
                $data_m_percent_ecn_stats""" + str(x) + """ << EOD
                """ + CollectionUtil.merge_testcase_data(testmeta, 'derived/m_percent_ecn_stats', self.x_axis) + """
                EOD
                $data_d_percent_nonecn_stats""" + str(x) + """ << EOD
                """ + CollectionUtil.merge_testcase_data(testmeta, 'derived/d_percent_nonecn_stats', self.x_axis) + """
                EOD"""

            plot += "$data_d_percent_ecn_stats" + str(x) + "     using ($1+" + str(x) + "+0.00):3:7:9" + xtics + " with yerrorbars lc rgb '" + Colors.DROPS_L4S + "' pointtype 7 pointsize 0.4 lw 1.5  title '" + ('Drops (ECN)' if is_first_set else '') + "', \\\n"
            plot += "''                                          using ($1+" + str(x) + "+0.00):6  with points  lc rgb '" + Colors.DROPS_L4S + "' pointtype 1 pointsize 0.4        title '', \\\n"
            plot += "''                                          using ($1+" + str(x) + "+0.00):10  with points  lc rgb '" + Colors.DROPS_L4S + "' pointtype 1 pointsize 0.4        title '', \\\n"
            plot += "$data_m_percent_ecn_stats" + str(x) + "     using ($1+" + str(x) + "+0.10):3:7:9 with yerrorbars lc rgb '" + Colors.MARKS_L4S + "' pointtype 7 pointsize 0.4 lw 1.5  title '" + ('Marks (ECN)' if is_first_set else '') + "', \\\n"
            plot += "''                                          using ($1+" + str(x) + "+0.10):6  with points  lc rgb '" + Colors.MARKS_L4S + "' pointtype 1 pointsize 0.4        title '', \\\n"
            plot += "''                                          using ($1+" + str(x) + "+0.10):10  with points  lc rgb '" + Colors.MARKS_L4S + "' pointtype 1 pointsize 0.4        title '', \\\n"
            plot += "$data_d_percent_nonecn_stats" + str(x) + "  using ($1+" + str(x) + "+0.20):3:7:9 with yerrorbars lc rgb '" + Colors.DROPS_CLASSIC + "' pointtype 7 pointsize 0.4 lw 1.5  title '" + ('Drops (Non-ECN)' if is_first_set else '') + "', \\\n"
            plot += "''                                          using ($1+" + str(x) + "+0.20):6  with points  lc rgb '" + Colors.DROPS_CLASSIC + "' pointtype 1 pointsize 0.4        title '', \\\n"
            plot += "''                                          using ($1+" + str(x) + "+0.20):10  with points  lc rgb '" + Colors.DROPS_CLASSIC + "' pointtype 1 pointsize 0.4        title '', \\\n"

            # gray lines between average values
            plot += "$data_d_percent_ecn_stats" + str(x) + "     using ($1+" + str(x) + "+0.00):3     with lines lc rgb 'gray'         title '', \\\n"
            plot += "$data_m_percent_ecn_stats" + str(x) + "     using ($1+" + str(x) + "+0.10):3     with lines lc rgb 'gray'         title '', \\\n"
            plot += "$data_d_percent_nonecn_stats" + str(x) + "  using ($1+" + str(x) + "+0.20):3     with lines lc rgb 'gray'         title '', \\\n"

        TreeUtil.walk_leaf(self.testmeta, data_drops)
        self.gpi += """
            plot \\
            """ + plot

    def common_header(self):
        ret = """
            unset bars
            set xtic rotate by -65 font ',""" + str(max(3, min(10, 15 - self.n_nodes / 18))) + """'
            set key above
            """

        if self.y_is_logarithmic:
            ret += """
            set logscale y
            """

        ret += """
            set xrange [-2:""" + str(self.n_nodes + 1) + """]
            set yrange [""" + ('0.1:105' if self.y_is_logarithmic else '0:*<105') + """]
            set boxwidth 0.2
            set tmargin """ + str(self.tmargin_base) + """
            set lmargin 13
            """

        return ret

    def plot(self, utilization_queues=True, utilization_tags=False):
        """Plot the test cases provided"""
        self.gpi = Plot.header()

        n_height = 2
        height = 14
        if utilization_queues:
            n_height += 1
            height += 7
        if utilization_tags:
            n_height += 1
            height += 7

        title = self.testmeta['title']
        if 'subtitle' in self.testmeta and self.testmeta['subtitle']:
            title += '\\n' + self.testmeta['subtitle']

        self.gpi += """
            set multiplot layout """ + str(n_height) + """,1 title \"""" + title + """\\n\" scale 1,1"""

        TreeUtil.walk_tree_reverse(self.testmeta, self.plot_labels)

        if utilization_queues:
            self.plot_utilization_queues()
        if utilization_tags:
            self.plot_utilization_tags()

        self.plot_queueing_delay()
        self.plot_drops_marks()

        self.gpi += """
            unset multiplot"""

        Plot.generate(self.output_file, self.gpi, size='21cm,%dcm' % height)


class Plot():
    gpi = ''
    size = '21cm,10cm'

    def generate(output_file, gpi, size='21cm,10cm'):
        gpi = """
            reset
            set terminal pdfcairo font 'Times-Roman,12' size """ + size + """
            set output '""" + output_file + """.pdf'
            """ + gpi

        # clean up whitespace at beginning of lines
        gpi = re.sub(r'^[\t ]+', '', gpi, 0, re.MULTILINE)

        with open(output_file + '.gpi', 'w') as f:
            f.write(gpi)

        local['gnuplot'][output_file + '.gpi'].run(stdin=None, stdout=None, stderr=None, retcode=None)

    @staticmethod
    def header():
        return """
            #set key above
            #set key box linestyle 99
            set key spacing 1.3
            set grid xtics ytics ztics lw 0.2 lc rgb 'gray'
            #set boxwidth 0.2 absolute

            #set xtic rotate by -65 offset 1
            #set style fill solid 1.0 border
            #set boxwidth 0.4

            # from https://github.com/aschn/gnuplot-colorbrewer
            # line styles for ColorBrewer Dark2
            # for use with qualitative/categorical data
            # provides 8 dark colors based on Set2
            # compatible with gnuplot >=4.2
            # author: Anna Schneider

            # line styles
            set style line 1 lc rgb '#1B9E77' # dark teal
            set style line 2 lc rgb '#D95F02' # dark orange
            set style line 3 lc rgb '#7570B3' # dark lilac
            set style line 4 lc rgb '#E7298A' # dark magenta
            set style line 5 lc rgb '#66A61E' # dark lime green
            set style line 6 lc rgb '#E6AB02' # dark banana
            set style line 7 lc rgb '#A6761D' # dark tan
            set style line 8 lc rgb '#666666' # dark gray

            # palette
            set palette maxcolors 8
            set palette defined ( 0 '#1B9E77',\
                                  1 '#D95F02',\
                                  2 '#7570B3',\
                                  3 '#E7298A',\
                                  4 '#66A61E',\
                                  5 '#E6AB02',\
                                  6 '#A6761D',\
                                  7 '#666666' )

            """

    def plot_compare_flows(self, folder, testfolders):
        hp = CollectionPlot(folder + '/analysis_compare', {
            'title': folder,
            'children': [{'testcase': x} for x in testfolders]
        })
        hp.plot()

    def plot_multiple_flows(self, testfolders, output_path):
        """Generate a PDF with one page with graphs per flow"""

        for testfolder in testfolders:
            self.plot_flow(testfolder, generate=False)

        Plot.generate(output_path, self.gpi, self.size)

    def plot_flow(self, testfolder, generate=True):
        """Generate a plot for a single test case"""

        self.size = '21cm,30cm'

        n_flows = 0
        flows = OrderedDict({
            'ecn': [],
            'nonecn': []
        })

        for (type, items) in flows.items():
            with open(testfolder + '/ta/flows_' + type, 'r') as f:
                for line in f:
                    items.append(line.strip())
                    n_flows += 1

        self.gpi += Plot.header()

        self.gpi += """
            set multiplot layout 4,1 columnsfirst title '""" + testfolder + """'
            set offset graph 0.02, graph 0.02, graph 0.02, graph 0.02
            set lmargin 13
            set yrange [0:]
            set xrange [1:""" + read_metadata(testfolder + '/details')[0]['ta_samples'] + """]
            set format y "%g"
            set ylabel 'Utilization per queue [%]'
            set style fill transparent solid 0.5 noborder
            set key above

            set style line 100 lt 1 lc rgb 'black' lw 1.5 dt 3
            set arrow 100 from graph 0, first 100 to graph 1, first 100 nohead ls 100 back

            stats '""" + testfolder + """/derived/util_tagged' using 1 nooutput
            plot \\
            """

        #ls 1 lw 1.5 lc variable
        self.gpi += "'" + testfolder + "/derived/util'    using ($0+1):($2*100)   with lines ls 1 lw 1.5 title 'Total utilization', \\\n"
        self.gpi += "''                                   using ($0+1):($3*100)   with lines ls 2 lw 1.5 title 'ECN utilization', \\\n"
        self.gpi += "''                                   using ($0+1):($4*100)   with lines ls 3 lw 1.5 title 'Non-ECN utilization', \\\n"

        self.gpi += "for [IDX=0:STATS_blocks-1] '" + testfolder + "/derived/util_tagged' index IDX using ($1+1):($2*100) with lines ls (IDX+3) title columnheader(1), \\\n"

        self.gpi += """

            unset arrow 100
            set format y "%.0f"
            set ylabel 'Rate per flow [b/s]'
            set key right center inside
            set logscale y
            set yrange [1000:]
            plot \\
            """

        if n_flows == 0:
            self.gpi += "0 title '',"

        for (type, items) in flows.items():
            j = 0
            for flow in items:
                pt = 2 if type == 'ecn' else 6
                ls = 2 if type == 'ecn' else 3
                self.gpi += "'" + testfolder + "/ta/r_pf_" + type + "'    using ($0+1):" + str(3 + j) + ":xtic($2/1000)   with linespoints ls " + str(ls) + " pointtype " + str(pt) + " ps 0.2 lw 1.5    title '" + type + " - " + flow + "', \\\n"
                j += 1

        self.gpi += """

            set ylabel "Queueing delay per queue [ms]\\n{/Times:Italic=10 (min, p_{25}, mean, p_{99}, max)}"
            unset bars
            set key above
            set xtics out nomirror
            unset logscale y
            set yrange [0:]
            plot \\
            """

        # 1=sample_id 2=min 3=p25 4=average 5=p99 6=max
        #             4     6     2         9    10
        self.gpi += "'" + testfolder + "/derived/qs_samples_ecn' using ($0+0.95):2:4:9 with yerrorbars ls 2 pointtype 7 ps 0.3 lw 1.5 title 'ECN packets', \\\n"
        self.gpi +=                                          "'' using ($0+0.95):2 with lines lc rgb 'gray'         title '', \\\n"
        self.gpi +=                                          "'' using ($0+0.95):10 with points  ls 2 pointtype 1 ps 0.3 lw 1.5 title '', \\\n"
        self.gpi +=                                          "'' using ($0+0.95):6 with points  ls 2 pointtype 1 ps 0.3 lw 1.5 title '', \\\n"
        self.gpi += "'" + testfolder + "/derived/qs_samples_nonecn' using ($0+1.05):2:4:9 with yerrorbars ls 3 pointtype 7 ps 0.3 lw 1.5 title 'Non-ECN packets', \\\n"
        self.gpi +=                                             "'' using ($0+1.05):2 with lines lc rgb 'gray'         title '', \\\n"
        self.gpi +=                                             "'' using ($0+1.05):10 with points  ls 3 pointtype 1 ps 0.3 lw 1.5 title '', \\\n"
        self.gpi +=                                             "'' using ($0+1.05):6 with points  ls 3 pointtype 1 ps 0.3 lw 1.5 title '', \\\n"

        self.gpi += """

            set format y "%g"
            set xlabel 'Sample #'
            set ylabel "Packets per sample\\n{/Times:Italic=10 Dotted lines are max packets in the queue}"
            set bars
            set logscale y
            set yrange [1:]
            set xtics in mirror
            set key above
            plot \\
            """

        self.gpi += "'" + testfolder + "/ta/d_tot_ecn'   using ($0+1):3 with linespoints pointtype 7 ps 0.2 lw 1.5 lc rgb 'red' title 'Drops (ECN)', \\\n"
        self.gpi += "'" + testfolder + "/ta/m_tot_ecn'   using ($0+1):3 with linespoints ls 8 pointtype 7 ps 0.2 lw 1.5 title 'Marks (ECN)', \\\n"
        self.gpi += "'" + testfolder + "/ta/d_tot_nonecn'   using ($0+1):3 with linespoints ls 3 pointtype 7 ps 0.2 lw 1.5 title 'Drops (Non-ECN)', \\\n"

        #self.gpi += "'" + testfolder + "/ta/tot_packets_ecn'   using ($0+1):1 with linespoints ls 8 dt 3 pointtype 7 ps 0.2 lw 1.5 title '', \\\n"
        #self.gpi += "'" + testfolder + "/ta/tot_packets_nonecn'   using ($0+1):1 with linespoints ls 3 dt 3 pointtype 7 ps 0.2 lw 1.5 title '', \\\n"

        self.gpi += """

            unset multiplot
            reset"""

        if generate:
            Plot.generate(testfolder + '/analysis', self.gpi, self.size)


class FolderUtil():

    @staticmethod
    def generate_hierarchy_data_from_folder(folder, swap_levels=[]):
        """Generate a dict that can be sent to CollectionPlot by analyzing the directory

        It will look in all the metadata stored while running test
        to generate the final result
        """

        def parse_folder(folder):
            if not os.path.isdir(folder):
                raise Exception('Non-existing directory: %s' % folder)

            metadata_kv, metadata_lines = read_metadata(folder + '/details')

            if 'type' not in metadata_kv:
                raise Exception('Missing type in metadata for %s' % folder)

            if metadata_kv['type'] in ['collection']:
                node = {
                    'title': metadata_kv['title'] if 'title' in metadata_kv else '',
                    'subtitle': metadata_kv['subtitle'] if 'subtitle' in metadata_kv else '',
                    'titlelabel': metadata_kv['titlelabel'] if 'titlelabel' in metadata_kv else '',
                    'children': []
                }

                for metadata in metadata_lines:
                    if metadata[0] == 'sub':
                        node['children'].append(parse_folder(folder + '/' + metadata[1]))

            elif metadata_kv['type'] == 'test':
                node = {
                    'testcase': folder
                }

            else:
                raise Exception('Unknown metadata type %s' % metadata_kv['type'])

            return node

        root = parse_folder(folder)

        # rearrange levels in the tree so the grouping is different
        for level in swap_levels:
            root = TreeUtil.swap_levels(root, level)

        return root


def read_metadata(file):
    """Reads metadata from a `details` file

    Returns a map of the properties as well as a list of properties to be used
    if properties of the same key is repeated
    """
    if not os.path.isfile(file):
        raise Exception('Missing metadata file: ' + file)

    metadata = {}
    lines = []

    with open(file, 'r') as f:
        for line in f:
            s = line.split(maxsplit=1)
            key = s[0]
            value = s[1].strip() if len(s) > 1 else ''
            metadata[key.strip()] = value
            lines.append((key, value))

    return (metadata, lines)

def plot_folder_compare(folder, swap_levels=[], x_axis=PlotAxis.CATEGORY, **kwargs):
    data = FolderUtil.generate_hierarchy_data_from_folder(folder, swap_levels)

    cp = CollectionPlot(folder + '/comparison', data, x_axis=x_axis)
    cp.plot(**kwargs)
    print('Plotted comparison of %s' % folder)

def plot_folder_flows(folder, swap_levels=[]):
    data = FolderUtil.generate_hierarchy_data_from_folder(folder, swap_levels)

    testcases = []
    def parse_leaf(testmeta, first_set, x):
        nonlocal testcases
        if len(testmeta['children']) == 0:
            return
        testcases += [item['children'][0]['testcase'] for item in testmeta['children']]
    TreeUtil.walk_leaf(data, parse_leaf)

    if len(testcases) > 0:
        output_path = '%s/analysis_merged' % folder
        plot = Plot()
        plot.plot_multiple_flows(testcases, output_path=output_path)
        print('Plotted merge of %s' % folder)

def plot_tests(folder):
    data = FolderUtil.generate_hierarchy_data_from_folder(folder)

    testcases = []
    def parse_leaf(testmeta, first_set, x):
        nonlocal testcases
        if len(testmeta['children']) == 0:
            return
        testcases += [item['children'][0]['testcase'] for item in testmeta['children']]
    TreeUtil.walk_leaf(data, parse_leaf)

    for testcase in testcases:
        p = Plot()
        p.plot_flow(testcase)
        print('Plotted %s' % testcase)

if __name__ == '__main__':
    def command_comparison(args):
        x_axis = PlotAxis.CATEGORY
        if args.logarithmic:
            x_axis = PlotAxis.LOGARITHMIC
        elif args.linear:
            x_axis = PlotAxis.LINEAR

        plot_folder_compare(
            args.folder,
            swap_levels=[] if args.swap == '' else [int(x) for x in args.swap.split(',')],
            x_axis=x_axis,
            utilization_queues=not args.nouq,
            utilization_tags=args.ut,
        )

    def command_merge(args):
        plot_folder_flows(
            args.folder,
            swap_levels=[] if args.swap == '' else [int(x) for x in args.swap.split(',')],
        )

    def command_plot_tests(args):
        plot_tests(args.folder)

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help='sub-command help')

    parser_a = subparsers.add_parser('comparison', help='plot a comparison for collections')
    parser_a.add_argument('folder', help='directory containing collections to include')
    parser_a.add_argument('-s', '--swap', help='list of levels to swap', default='')
    parser_a.add_argument('--nouq', help='skip utilization plot for each queue', action='store_true')
    parser_a.add_argument('--ut', help='include utilization plot for each tag', action='store_true')
    axis = parser_a.add_mutually_exclusive_group()
    axis.add_argument('--logarithmic', help='plot X axis logarithmic instead of by category', action='store_true')
    axis.add_argument('--linear', help='plot X axis linearly instead of by category', action='store_true')
    parser_a.set_defaults(func=command_comparison)

    parser_b = subparsers.add_parser('merge', help='merge plots from multiple tests')
    parser_b.add_argument('folder', help='directory containing collections to include')
    parser_b.add_argument('-s', '--swap', help='list of levels to swap', default='')
    parser_b.set_defaults(func=command_merge)

    parser_c = subparsers.add_parser('tests', help='individual plots for tests')
    parser_c.add_argument('folder', help='directory containg collections to inclued')
    parser_c.set_defaults(func=command_plot_tests)

    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()
