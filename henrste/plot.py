#!/usr/bin/env python3
from plumbum import local
import os.path
import os
import re
import sys
from pprint import pprint
from collections import OrderedDict

color_cubic = "#FC6C6C"
color_dctcp = "blue"
color_udp_l4s = "purple"
color_ecn_cubic = "black"
color_reno = "brown"
color_util = "orange"

class HierarchyPlot():
    """Plot a collection of test cases

    It is assumed that all leafs are of the same structure,
    but not necessary same amount of test cases inside
    a leaf
    """

    def __init__(self, output_file, testmeta):
        self.plotutils = Plot()
        self.gpi = ''
        self.testmeta = testmeta
        self.output_file = output_file

        self.n_sets, self.n_tests, self.n_depth, self.n_nodes = HierarchyPlot.get_num_testcases(testmeta)

        self.tmargin_base = 1 * self.n_depth + 2
        if 'subtitle' in self.testmeta and self.testmeta['subtitle']:
            self.tmargin_base += .8

        self.depth_sizes = HierarchyPlot.get_depth_sizes(testmeta)

    @staticmethod
    def get_depth_sizes(testmeta):
        depths = {}

        def check_node(item, x, depth):
            if depth not in depths:
                depths[depth] = 0
            depths[depth] += 1

        HierarchyPlot.walk_tree_set(testmeta, check_node)
        return depths

    @staticmethod
    def get_num_testcases(testmeta):
        """Returns a tuple of numbers sets, tests and depth"""

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
    def walk_tree_leaf_set(testmeta, fn):
        """Walks the tree and calls fn for every leaf collection"""

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
    def walk_tree_set_reverse(testmeta, fn):
        """Walks the tree and calls fn for every collection in reverse order"""
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
    def walk_tree_set(testmeta, fn, include_test_node=False):
        """Walks the tree and calls fn for every tree node"""
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
    def get_testcases(testmeta):
        """Get list of testcases of a test set"""
        return [(item['title'], item['children'][0]['testcase']) for item in testmeta['children']]

    @staticmethod
    def merge_testcase_data(testmeta, statsname):
        # testmeta -> testcases

        out = []
        for title, testcase_folder in HierarchyPlot.get_testcases(testmeta):
            with open(testcase_folder + '/' + statsname, 'r') as f:
                for line in f:
                    if line.startswith('#'):
                        continue

                    out.append('"%s" %s' % (title, line))

        return ''.join(out)

    @staticmethod
    def merge_testcase_data_group(testmeta, statsname):
        """Similar to merge_testcase_data except it groups all data by first column"""
        out = OrderedDict()

        for title, testcase_folder in HierarchyPlot.get_testcases(testmeta):
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
                        out[group_by] = []

                    out[group_by].append('"%s" %s' % (title, line))

        for key in out.keys():
            out[key] = ''.join(out[key])

        return out

    def plot_labels(self, testmeta, x, depth, width):
        fontsize = fontsize = max(5, min(9, 10 - self.depth_sizes[depth] / 4.5))

        self.gpi += """
            #set label '""" + testmeta['title'] + """' at first """ + str(x+(width-2)/2) + """, graph """ + str(1.05 + 0.06 * (self.n_depth - depth - 1)) + """ font 'Times-Roman,9pt' tc rgb 'black' center
            set label \"""" + testmeta['title'] + """\" at first """ + str(x) + """, graph """ + str(1.05 + 0.06 * (self.n_depth - depth - 1)) + """ font 'Times-Roman,""" + str(fontsize) + """pt' tc rgb 'black' left"""

    def plot_utilization_queues(self):
        """Plot graph of utilization for total, ECN and non-ECN flows"""
        self.gpi += self.common_header()
        self.gpi += """

            # utilization
            set style line 100 lt 1 lc rgb 'black' lw 1.5 dt 3
            set arrow 100 from graph 0, first 100 to graph 1, first 100 nohead ls 100 back

            set ylabel "Percent\\n{/Times:Italic=10 (p_1, mean, p_{99})}" """

        plot = ''
        titles_used = []
        def data_util(testmeta, is_first_set, x):
            nonlocal plot, titles_used

            self.gpi += """
                $dataUtil""" + str(x) + """ << EOD
                """ + HierarchyPlot.merge_testcase_data(testmeta, 'util_stats') + """
                EOD"""

            # total
            plot += "$dataUtil" + str(x) + "  using ($0+" + str(x) + "+0.0):5:7:3       with yerrorbars ls 1 pointtype 7 pointsize 0.5 lw 1.5 title '" + ('Total utilization' if is_first_set else '') + "', "
            plot += "                      '' using ($0+" + str(x) + "+0.0):5  with lines lc rgb 'gray'         title '', "
            #plot += "                      '' using ($0+" + str(x) + "+0.0):4  with points  ls 1 pointtype 1 pointsize 0.4        title '', "
            #plot += "                      '' using ($0+" + str(x) + "+0.0):6  with points  ls 1 pointtype 1 pointsize 0.4        title '', "

            # ecn
            plot += "                      '' using ($0+" + str(x) + "+0.1):10:8:12:xtic(1)    with yerrorbars ls 2 pointtype 7 pointsize 0.5 lw 1.5 title '" + ('ECN utilization' if is_first_set else '') + "', "
            plot += "                      '' using ($0+" + str(x) + "+0.1):10  with lines lc rgb 'gray'         title '', "
            #plot += "                      '' using ($0+" + str(x) + "+0.1):9   with points  ls 2 pointtype 1 pointsize 0.4        title '', "
            #plot += "                      '' using ($0+" + str(x) + "+0.1):11  with points  ls 2 pointtype 1 pointsize 0.4        title '', "

            # nonecn
            plot += "                      '' using ($0+" + str(x) + "+0.2):15:13:17  with yerrorbars ls 3 pointtype 7 pointsize 0.5 lw 1.5 title '" + ('Non-ECN utilization' if is_first_set else '') + "', "
            plot += "                      '' using ($0+" + str(x) + "+0.2):15  with lines lc rgb 'gray'         title '', "
            #plot += "                      '' using ($0+" + str(x) + "+0.2):14  with points  ls 3 pointtype 1 pointsize 0.4        title '', "
            #plot += "                      '' using ($0+" + str(x) + "+0.2):16  with points  ls 3 pointtype 1 pointsize 0.4        title '', "

        HierarchyPlot.walk_tree_leaf_set(self.testmeta, data_util)
        self.gpi += """
            plot """ + plot + """
            unset arrow 100"""

    def plot_utilization_tags(self):
        self.gpi += self.common_header()
        self.gpi += """

            # utilization of tags
            set style line 100 lt 1 lc rgb 'black' lw 1.5 dt 3
            set arrow 100 from graph 0, first 100 to graph 1, first 100 nohead ls 100 back

            set ylabel "Percent\\n{/Times:Italic=10 (p_{25}, mean, p_{75})}" """

        plot = ''
        titles_used = []
        def data_util_tags(testmeta, is_first_set, x):
            nonlocal plot, titles_used

            self.gpi += """
                $dataUtil""" + str(x) + """ << EOD
                """ + HierarchyPlot.merge_testcase_data(testmeta, 'util_stats') + """
                EOD"""

            # total
            # 5:7:3
            plot += "$dataUtil" + str(x) + "  using ($0+" + str(x) + "+0.0):5:6:4:xtic(1)       with yerrorbars ls 1 pointtype 7 pointsize 0.5 lw 1.5 title '" + ('Total utilization' if is_first_set else '') + "', "
            plot += "                      '' using ($0+" + str(x) + "+0.0):5  with lines lc rgb 'gray'         title '', "

            tagged_flows = HierarchyPlot.merge_testcase_data_group(testmeta, 'util_tagged_stats')
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

                plot += "$dataUtil" + str(x) + "_" + str(i) + "  using ($0+" + str(x+((i+1) * x_distance)) + "):($6*100):($7*100):($5*100)       with yerrorbars ls " + ls + " pointtype 7 pointsize 0.5 lw 1.5 title '" + title + "', "
                plot += "                                     '' using ($0+" + str(x+((i+1) * x_distance)) + "):($6*100) with lines lc rgb 'gray' title '', "

        HierarchyPlot.walk_tree_leaf_set(self.testmeta, data_util_tags)

        self.gpi += """
            set tmargin """ + str(self.tmargin_base + 1.3 * (len(titles_used)+1) / 4 - 1) + """

            plot """ + plot + """
            unset arrow 100"""

    def plot_queueing_delay(self):
        self.gpi += self.common_header()
        self.gpi += """

            # queueing delay
            set yrange [0:*]
            set ylabel "Queueing delay [ms]\\n{/Times:Italic=10 (p_1, p_{25}, mean, p_{75}, p_{99})}
            #set xtic offset first .1"""

        plot = ''
        def data_rate(testmeta, is_first_set, x):
            nonlocal plot

            self.gpi += """
                $data_qs_ecn_stats""" + str(x) + """ << EOD
                """ + HierarchyPlot.merge_testcase_data(testmeta, 'qs_ecn_stats') + """
                EOD
                $data_qs_nonecn_stats""" + str(x) + """ << EOD
                """ + HierarchyPlot.merge_testcase_data(testmeta, 'qs_nonecn_stats') + """
                EOD"""

            plot += "$data_qs_ecn_stats" + str(x) + "    using ($0+" + str(x) + "+0.05):3:5:4:xtic(1)   with yerrorbars ls 2 lw 1.5 pointtype 7 pointsize 0.5            title '" + ('ECN packets' if is_first_set else '') + "', "
            plot += "                              ''    using ($0+" + str(x) + "+0.05):3  with lines lc rgb 'gray'         title '', "
            plot += "                              ''    using ($0+" + str(x) + "+0.05):6  with points  ls 2 pointtype 1 pointsize 0.4        title '', "
            plot += "                              ''    using ($0+" + str(x) + "+0.05):7  with points  ls 2 pointtype 1 pointsize 0.4        title '', "
            plot += "$data_qs_nonecn_stats" + str(x) + " using ($0+" + str(x) + "+0.15):3:5:4  with yerrorbars ls 3 lw 1.5 pointtype 7 pointsize 0.5           title '" + ('Non-ECN packets' if is_first_set else '') + "', "
            plot += "                              ''    using ($0+" + str(x) + "+0.15):3  with lines lc rgb 'gray'         title '', "
            plot += "                              ''    using ($0+" + str(x) + "+0.15):6  with points  ls 3 pointtype 1 pointsize 0.4        title '', "
            plot += "                              ''    using ($0+" + str(x) + "+0.15):7  with points  ls 3 pointtype 1 pointsize 0.4        title '', "

        HierarchyPlot.walk_tree_leaf_set(self.testmeta, data_rate)
        self.gpi += """
            plot """ + plot

    def plot_drops_marks(self):
        self.gpi += self.common_header()
        self.gpi += """

            # drops and marks
            set ylabel "Percent\\n{/Times:Italic=10 (p_1, p_{25}, mean, p_{75}, p_{99})}
            set xtic offset first 0"""

        # show xlabel at bottom of the multiplot
        if 'xlabel' in self.testmeta and self.testmeta['xlabel'] is not None and len(self.testmeta['xlabel']) > 0:
            self.gpi += """
                set xlabel '""" + self.testmeta['xlabel'] + """'"""

        plot = ''
        def data_drops(testmeta, is_first_set, x):
            nonlocal plot

            self.gpi += """
                $data_d_percent_ecn_stats""" + str(x) + """ << EOD
                """ + HierarchyPlot.merge_testcase_data(testmeta, 'd_percent_ecn_stats') + """
                EOD
                $data_m_percent_ecn_stats""" + str(x) + """ << EOD
                """ + HierarchyPlot.merge_testcase_data(testmeta, 'm_percent_ecn_stats') + """
                EOD
                $data_d_percent_nonecn_stats""" + str(x) + """ << EOD
                """ + HierarchyPlot.merge_testcase_data(testmeta, 'd_percent_nonecn_stats') + """
                EOD"""

            plot += "$data_d_percent_ecn_stats" + str(x) + "     using ($0+" + str(x) + "+0.00):3:5:4 with yerrorbars lc rgb 'red' pointtype 7 pointsize 0.5 lw 1.5  title '" + ('Drops (ECN)' if is_first_set else '') + "', "
            plot += "                                         '' using ($0+" + str(x) + "+0.00):3     with lines lc rgb 'gray'         title '', "
            plot += "                                         '' using ($0+" + str(x) + "+0.00):6  with points  lc rgb 'red' pointtype 1 pointsize 0.4        title '', "
            plot += "                                         '' using ($0+" + str(x) + "+0.00):7  with points  lc rgb 'red' pointtype 1 pointsize 0.4        title '', "
            plot += "$data_m_percent_ecn_stats" + str(x) + "     using ($0+" + str(x) + "+0.10):3:5:4:xtic(1) with yerrorbars ls 8 pointtype 7 pointsize 0.5 lw 1.5  title '" + ('Marks (ECN)' if is_first_set else '') + "', "
            plot += "                                         '' using ($0+" + str(x) + "+0.10):3     with lines lc rgb 'gray'         title '', "
            plot += "                                         '' using ($0+" + str(x) + "+0.10):6  with points  ls 8 pointtype 1 pointsize 0.4        title '', "
            plot += "                                         '' using ($0+" + str(x) + "+0.10):7  with points  ls 8 pointtype 1 pointsize 0.4        title '', "
            plot += "$data_d_percent_nonecn_stats" + str(x) + "  using ($0+" + str(x) + "+0.20):3:5:4 with yerrorbars ls 3 pointtype 7 pointsize 0.5 lw 1.5  title '" + ('Drops (Non-ECN)' if is_first_set else '') + "', "
            plot += "                                         '' using ($0+" + str(x) + "+0.20):3     with lines lc rgb 'gray'         title '', "
            plot += "                                         '' using ($0+" + str(x) + "+0.20):6  with points  ls 3 pointtype 1 pointsize 0.4        title '', "
            plot += "                                         '' using ($0+" + str(x) + "+0.20):7  with points  ls 3 pointtype 1 pointsize 0.4        title '', "

        HierarchyPlot.walk_tree_leaf_set(self.testmeta, data_drops)
        self.gpi += """
            plot """ + plot

    def common_header(self):
        return """
            unset bars
            set xtic rotate by -65 font ',""" + str(min(10, 15 - self.n_nodes / 18)) + """'
            set key above

            set xrange [-2:""" + str(self.n_nodes + 1) + """]
            set yrange [0:*<105]
            set boxwidth 0.2
            set tmargin """ + str(self.tmargin_base) + """
            set lmargin 13"""

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

        HierarchyPlot.walk_tree_set_reverse(self.testmeta, self.plot_labels)

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
        hp = HierarchyPlot(folder + '/analysis_compare', {
            'title': folder,
            #'xlabel': 'something',
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
            with open(testfolder + '/flows_' + type, 'r') as f:
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
            set ylabel 'Utilization in %'
            set style fill transparent solid 0.5 noborder
            set key above

            set style line 100 lt 1 lc rgb 'black' lw 1.5 dt 3
            set arrow 100 from graph 0, first 100 to graph 1, first 100 nohead ls 100 back

            stats '""" + testfolder + """/util_tagged' using 1 nooutput
            plot """

        #ls 1 lw 1.5 lc variable
        self.gpi += "'" + testfolder + "/util'    using ($0+1):($2*100)   with lines ls 1 lw 1.5 title 'Total utilization', "
        self.gpi += "                       ''    using ($0+1):($3*100)   with lines ls 2 lw 1.5 title 'ECN utilization', "
        self.gpi += "                       ''    using ($0+1):($4*100)   with lines ls 3 lw 1.5 title 'Non-ECN utilization', "

        self.gpi += "for [IDX=0:STATS_blocks-1] '" + testfolder + "/util_tagged' index IDX using ($1+1):($2*100) with lines ls (IDX+3) title columnheader(1),"

        self.gpi += """

            unset arrow 100
            set format y "%.0f"
            set ylabel 'Rate [b/s]'
            set key right center inside
            plot """

        if n_flows == 0:
            self.gpi += "0 title '',"

        for (type, items) in flows.items():
            j = 0
            for flow in items:
                pt = 2 if type == 'ecn' else 6
                ls = 2 if type == 'ecn' else 3
                self.gpi += "'" + testfolder + "/r_pf_" + type + "'    using ($0+1):" + str(3 + j) + ":xtic($2/1000)   with linespoints ls " + str(ls) + " pointtype " + str(pt) + " ps 0.2 lw 1.5    title '" + type + " - " + flow + "', "
                j += 1

        self.gpi += """
            set ylabel "Queueing delay [ms]\\n{/Times:Italic=10 (min, p_{25}, mean, p_{99}, max)}"
            unset bars
            set key above
            set xtics out nomirror
            plot """

        # 1=sample_id 2=min 3=p25 4=average 5=p99 6=max
        self.gpi += "'" + testfolder + "/qs_samples_ecn' using ($0+0.95):4:2:5 with yerrorbars ls 2 pointtype 7 ps 0.3 lw 1.5 title 'ECN packets', "
        self.gpi +=                                  "'' using ($0+0.95):4 with lines lc rgb 'gray'         title '', "
        self.gpi +=                                  "'' using ($0+0.95):6 with points  ls 2 pointtype 1 ps 0.3 lw 1.5 title '', "
        self.gpi +=                                  "'' using ($0+0.95):3 with points  ls 2 pointtype 1 ps 0.3 lw 1.5 title '', "
        self.gpi += "'" + testfolder + "/qs_samples_nonecn' using ($0+1.05):4:2:5 with yerrorbars ls 3 pointtype 7 ps 0.3 lw 1.5 title 'Non-ECN packets', "
        self.gpi +=                                     "'' using ($0+1.05):4 with lines lc rgb 'gray'         title '', "
        self.gpi +=                                     "'' using ($0+1.05):6 with points  ls 3 pointtype 1 ps 0.3 lw 1.5 title '', "
        self.gpi +=                                     "'' using ($0+1.05):3 with points  ls 3 pointtype 1 ps 0.3 lw 1.5 title '', "

        self.gpi += """
            set format y "%g"
            set xlabel 'Sample #'
            set ylabel "Packets per sample\\n{/Times:Italic=10 Dotted lines are max packets in the queue}"
            set bars
            set xtics in mirror
            set key above
            plot """

        self.gpi += "'" + testfolder + "/d_tot_ecn'   using ($0+1):3 with linespoints pointtype 7 ps 0.2 lw 1.5 lc rgb 'red' title 'Drops (ECN)', "
        self.gpi += "'" + testfolder + "/m_tot_ecn'   using ($0+1):3 with linespoints ls 8 pointtype 7 ps 0.2 lw 1.5 title 'Marks (ECN)', "
        self.gpi += "'" + testfolder + "/d_tot_nonecn'   using ($0+1):3 with linespoints ls 3 pointtype 7 ps 0.2 lw 1.5 title 'Drops (Non-ECN)', "

        #self.gpi += "'" + testfolder + "/tot_packets_ecn'   using ($0+1):1 with linespoints ls 8 dt 3 pointtype 7 ps 0.2 lw 1.5 title '', "
        #self.gpi += "'" + testfolder + "/tot_packets_nonecn'   using ($0+1):1 with linespoints ls 3 dt 3 pointtype 7 ps 0.2 lw 1.5 title '', "

        self.gpi += """
            unset multiplot
            reset"""

        if generate:
            Plot.generate(testfolder + '/analysis', self.gpi, self.size)


def get_testcases_in_folder(folder):
    testcases = []

    for file in os.listdir(folder):
        if file.startswith('test-') and os.path.isdir(os.path.join(folder, file)):
            # verify the test contains analyzed data
            with open(os.path.join(folder, file, 'details')) as f:
                for line in f:
                    if line == 'data_analyzed':
                        testcases.append(os.path.join(folder, file))
                        continue

    return sorted(testcases)


def generate_hierarchy_data(folderspec, title, xlabel=''):
    """Generate a dict that can be sent to HierarchyPlot

    Example:
        data = generate_hierarchy_data({
            '1 flow each': {
                'cubic vs cubic': 'testset-simple/flows-1/cubic',
                'cubic vs cubic-ecn': 'testset-simple/flows-1/cubic-ecn',
                'cubic vs dctcp': 'testset-simple/flows-1/dctcp',
            },
            '2 flow each': {
                'cubic vs cubic': 'testset-simple/flows-2/cubic',
                'cubic vs cubic-ecn': 'testset-simple/flows-2/cubic-ecn',
                'cubic vs dctcp': 'testset-simple/flows-2/dctcp',
            },
            '3 flow each': {
                'cubic vs cubic': 'testset-simple/flows-3/cubic',
                'cubic vs cubic-ecn': 'testset-simple/flows-3/cubic-ecn',
                'cubic vs dctcp': 'testset-simple/flows-3/dctcp',
            },
        }, title='Testing cubic vs different flows', xlabel='RTT')

    See also generate_hierarchy_data_from_folder which does
    the similar process just from a directory structure with metadata
    """

    root = {
        'title': title,
        'xlabel': xlabel,
        'children': []
    }

    def add_level(root, spec):
        for key, value in spec.items():
            node = {'title': key, 'children': []}
            root['children'].append(node)

            if isinstance(value, dict):
                add_level(node, value)

            else:
                for testcase in get_testcases_in_folder(value):
                    metadata_kv, metadata_lines = read_metadata(testcase + '/details')

                    node['children'].append({
                        'title': metadata_kv['title'],
                        'titlelabel': metadata_kv['titlelabel'] if 'titlelabel' in metadata_kv else '',
                        'subtitle': '',
                        'children': [
                            {'testcase': testcase}
                        ]
                    })

    add_level(root, folderspec)
    return root

def read_metadata(file):
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

def generate_hierarchy_data_from_folder(folder):
    """Generate a dict that can be sent to HierarchyPlot by analyzing the directory

    It will look in all the metadata stored while running test
    to generate the final result
    """

    xlabel = None

    def parse_folder(folder):
        nonlocal xlabel

        if not os.path.isdir(folder):
            raise Exception('Non-existing directory: %s' % folder)

        metadata_kv, metadata_lines = read_metadata(folder + '/details')

        if 'type' not in metadata_kv:
            raise Exception('Missing type in metadata for %s' % folder)

        if metadata_kv['type'] in ['collection', 'set']:
            node = {
                'title': metadata_kv['title'] if 'title' in metadata_kv else '',
                'subtitle': metadata_kv['subtitle'] if 'subtitle' in metadata_kv else '',
                'children': []
            }

            for metadata in metadata_lines:
                if metadata[0] == 'sub':
                    node['children'].append(parse_folder(folder + '/' + metadata[1]))

        elif metadata_kv['type'] == 'test':
            node = {
                'title': metadata_kv['title'],
                'titlelabel': metadata_kv['titlelabel'] if 'titlelabel' in metadata_kv else '',
                'subtitle': '',
                'children': [
                    {'testcase': folder}
                ]
            }

            if xlabel is None and 'titlelabel' in metadata_kv:
                xlabel = metadata_kv['titlelabel']

        else:
            raise Exception('Unknown metadata type %s' % metadata_kv['type'])

        return node

    root = parse_folder(folder)
    root['xlabel'] = xlabel

    return root

def hierarchy_swap_levels(spec, level=0):
    """Rotate order data is grouped to columns"""

    if level > 0:
        def walk(testmeta, depth):
            if len(testmeta['children']) == 0:
                return

            # is this a set of tests?
            if 'testcase' in testmeta['children'][0]:
                return

            for index, item in enumerate(testmeta['children']):
                if depth + 1 == level:
                    testmeta['children'][index] = hierarchy_swap_levels(item)
                else:
                    walk(item, depth + 1)

        walk(spec, 0)
        return spec

    titles = []
    def check_level(item, x, depth):
        nonlocal titles
        if depth == 1 and item['title'] not in titles:
            titles.append(item['title'])
    HierarchyPlot.walk_tree_set(spec, check_level, include_test_node=True)

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

    HierarchyPlot.walk_tree_set(spec, build_swap, include_test_node=True)

    spec['children'] = [val for key, val in new_children.items()]
    return spec

def plot_folder_compare(folder, swap_levels=[], **kwargs):
    data = generate_hierarchy_data_from_folder(folder)

    for level in swap_levels:
        data = hierarchy_swap_levels(data, level)

    hp = HierarchyPlot(folder + '/comparison', data)
    hp.plot(**kwargs)

def plot_folder_flows(folder):
    data = generate_hierarchy_data_from_folder(folder)

    def parse_set(testmeta, first_set, x):
        if len(testmeta['children']) == 0:
            return

        testcases = [item['testcase'] for item in testmeta['children']]

        # assume all tests referred to is in the same folder, so use the parent folder
        set_folder = os.path.dirname(testcases[0].rstrip('/'))
        if set_folder == '':
            set_folder = '.'

        plot = Plot()
        plot.plot_multiple_flows(testcases, output_path='%s/analysis_merged' % set_folder)

    HierarchyPlot.walk_tree_leaf_set(data, parse_set)


if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == 'collection':
        folder = sys.argv[2]
        swap_levels = []
        if len(sys.argv) >= 4 and sys.argv[3] != '':
            swap_levels = [int(x) for x in sys.argv[3].split(',')]

        utilization_queues = True
        utilization_tags = False

        if len(sys.argv) >= 5:
            if 'nouq' in sys.argv[4].split(','):
                utilization_queues = False
            if 'ut' in sys.argv[4].split(','):
                utilization_tags = True

        plot_folder_compare(folder, swap_levels=swap_levels,
                            utilization_queues=utilization_queues, utilization_tags=utilization_tags)

    elif len(sys.argv) >= 3 and sys.argv[1] == 'flows':
        folder = sys.argv[2]
        plot_folder_flows(folder)

    else:
        print('Syntax:')
        print('  ./plot.py collection <topdirectory> [<swap level>,..] [nouq,ut]')
        print('  ./plot.py flows <topdirectory> [<swap level>,..]')
