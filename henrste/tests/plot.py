#!/usr/bin/env python3
from plumbum import local
import os.path
import os
import re
from pprint import pprint
import unittest

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

    def __init__(self):
        self.plotutils = Plot()

    def get_num_testcases(self, testmeta):
        """Returns a tuple of numbers sets, tests and depth"""

        sets = 0
        tests = 0
        depth = 0

        def traverse(testmeta, depthnow=0):
            nonlocal sets, tests, depth
            f = testmeta['children'][0]

            if depthnow > depth:
                depth = depthnow

            # is this a set of tests?
            if 'testcase' in f:
                tests += len(testmeta['children'])
                sets += 1

            # or is it a list of sets
            else:
                for item in testmeta['children']:
                    traverse(item, depthnow + 1)

        traverse(testmeta)
        return (sets, tests, depth)

    def walk_tree_leaf_set(self, testmeta, fn):
        """Walks the tree and calls fn for every leaf set"""

        first_set = True
        x = 0

        def walk(testmeta):
            nonlocal first_set, x

            if len(testmeta['children']) == 0:
                return

            f = testmeta['children'][0]

            # is this a set of tests?
            if 'testcase' in f:
                fn(testmeta, first_set, x)
                first_set = False
                x += len(testmeta['children'])

            # or is it a list of sets
            else:
                for item in testmeta['children']:
                    walk(item)

            x += 1

        walk(testmeta)

    def walk_tree_set(self, testmeta, fn):
        """Walks the tree and calls fn for every set in reverse order"""
        x = 0

        def walk(testmeta, depth):
            nonlocal x

            if len(testmeta['children']) == 0:
                return

            f = testmeta['children'][0]

            # is this a set of tests?
            if 'testcase' in f:
                x += len(testmeta['children'])

            # or is it a list of sets
            else:
                for item in testmeta['children']:
                    y = x
                    walk(item, depth + 1)
                    fn(item, y, depth, x - y)

            x += 1

        walk(testmeta, 0)

    def plot(self, outfile, testmeta):
        """Plot the test cases provided"""

        n_sets, n_tests, n_depth = self.get_num_testcases(testmeta)
        num = n_sets + n_tests

        self.plotutils.size = '21cm,22cm'
        self.plotutils.header()

        def plot_labels(testmeta, x, depth, width):
            self.plotutils.gpi += """
                set label '""" + testmeta['title'] + """' at first """ + str(x+(width-2)/2) + """, graph """ + str(1.05 + 0.07 * (n_depth - depth - 1)) + """ font 'Times-Roman,8pt' tc rgb 'black' center"""

        self.plotutils.gpi += """
            set multiplot layout 3,1 title '""" + testmeta['title'] + """'

            unset bars
            set xtic rotate by -65 font ',8pt'
            set key above

            #set title '""" + testmeta['title'] + """'
            set xrange [-.6:""" + str(num-2) + """.9]
            set yrange [0:]
            set boxwidth 0.2
            set tmargin """ + str(1 * n_depth + 2) + """
            set lmargin 13"""


        self.plotutils.gpi += """

            #set style line 100 lt 1 lc rgb 'red' lw 2
            #set arrow 100 from 1,-1 to 1,1 nohead ls 100 front
            #set arrow 100 from graph 0, second 100 to graph 1, second 100 nohead ls 100 front

            #set xtic offset first .3
            set ylabel "Percent\\n{/Times:Italic=10 (p_1, mean, p_{99})}" """

        self.walk_tree_set(testmeta, plot_labels)

        plot = ''
        def data_util(testmeta, is_first_set, x):
            nonlocal plot

            self.plotutils.gpi += """
                $dataUtil""" + str(x) + """ << EOD
                """ + self.plotutils.mergeTestcaseData(testmeta['children'], 'util_stats') + """
                EOD"""

            plot += "$dataUtil" + str(x) + "  using ($0+" + str(x) + "+0.0):3:5:4       with yerrorbars ls 1 pointtype 7 pointsize 0.5 lw 1.5 title '" + ('Total utilization' if is_first_set else '') + "', "
            plot += "                      '' using ($0+" + str(x) + "+0.0):3  with lines lc rgb 'gray'         title '', "
            plot += "                      '' using ($0+" + str(x) + "+0.1):6:8:7:xtic(1)    with yerrorbars ls 2 pointtype 7 pointsize 0.5 lw 1.5 title '" + ('ECN utilization' if is_first_set else '') + "', "
            plot += "                      '' using ($0+" + str(x) + "+0.1):6  with lines lc rgb 'gray'         title '', "
            plot += "                      '' using ($0+" + str(x) + "+0.2):9:10:11  with yerrorbars ls 3 pointtype 7 pointsize 0.5 lw 1.5 title '" + ('Non-ECN utilization' if is_first_set else '') + "', "
            plot += "                      '' using ($0+" + str(x) + "+0.2):9  with lines lc rgb 'gray'         title '', "

        self.walk_tree_leaf_set(testmeta, data_util)
        self.plotutils.gpi += """
            plot """ + plot + """
            set ylabel "Queueing delay [ms]\\n{/Times:Italic=10 (p_1, mean, p_{99})}"
            set xtic offset first .15"""

        plot = ''
        def data_rate(testmeta, is_first_set, x):
            nonlocal plot

            self.plotutils.gpi += """
                $data_qs_ecn_stats""" + str(x) + """ << EOD
                """ + self.plotutils.mergeTestcaseData(testmeta['children'], 'qs_ecn_stats') + """
                EOD
                $data_qs_nonecn_stats""" + str(x) + """ << EOD
                """ + self.plotutils.mergeTestcaseData(testmeta['children'], 'qs_nonecn_stats') + """
                EOD"""

            plot += "$data_qs_ecn_stats" + str(x) + "    using ($0+" + str(x) + "+0.05):3:5:4:xtic(1)   with yerrorbars ls 3 lw 1.5 pointtype 7 pointsize 0.5            title '" + ('ECN queue' if is_first_set else '') + "', "
            plot += "                              ''    using ($0+" + str(x) + "+0.05):3  with lines lc rgb 'gray'         title '', "
            plot += "$data_qs_nonecn_stats" + str(x) + " using ($0+" + str(x) + "+0.15):3:5:4  with yerrorbars ls 5 lw 1.5 pointtype 7 pointsize 0.5           title '" + ('Non-ECN queue' if is_first_set else '') + "', "
            plot += "                              ''    using ($0+" + str(x) + "+0.15):3  with lines lc rgb 'gray'         title '', "

        self.walk_tree_leaf_set(testmeta, data_rate)
        self.plotutils.gpi += """
            plot """ + plot + """
            #set xtic offset first .10
            set ylabel "Percent\\n{/Times:Italic=10 (p_1, mean, p_{99})}" """

        if 'xlabel' in testmeta and len(testmeta['xlabel']) > 0:
            self.plotutils.gpi += """
                set xlabel '""" + testmeta['xlabel'] + """'"""

        plot = ''
        def data_drops(testmeta, is_first_set, x):
            nonlocal plot

            self.plotutils.gpi += """
                $data_d_percent_nonecn_stats""" + str(x) + """ << EOD
                """ + self.plotutils.mergeTestcaseData(testmeta['children'], 'd_percent_nonecn_stats') + """
                EOD
                $data_d_percent_ecn_stats""" + str(x) + """ << EOD
                """ + self.plotutils.mergeTestcaseData(testmeta['children'], 'd_percent_ecn_stats') + """
                EOD
                $data_m_percent_ecn_stats""" + str(x) + """ << EOD
                """ + self.plotutils.mergeTestcaseData(testmeta['children'], 'm_percent_ecn_stats') + """
                EOD"""

            plot += "$data_d_percent_nonecn_stats" + str(x) + "  using ($0+" + str(x) + "+0.0):3:5:4 with yerrorbars ls 3 pointtype 7 pointsize 0.5 lw 1.5  title '" + ('Drops (Non-ECN)' if is_first_set else '') + "', "
            plot += "                                         '' using ($0+" + str(x) + "+0.0):3     with lines lc rgb 'gray'         title '', "
            plot += "$data_d_percent_ecn_stats" + str(x) + "     using ($0+" + str(x) + "+0.10):3:5:4:xtic(1) with yerrorbars lc rgb 'red' pointtype 7 pointsize 0.5 lw 1.5  title '" + ('Drops (ECN)' if is_first_set else '') + "', "
            plot += "                                         '' using ($0+" + str(x) + "+0.10):3     with lines lc rgb 'gray'         title '', "
            plot += "$data_m_percent_ecn_stats" + str(x) + "     using ($0+" + str(x) + "+0.20):3:5:4 with yerrorbars ls 8 pointtype 7 pointsize 0.5 lw 1.5  title '" + ('Marks (ECN)' if is_first_set else '') + "', "
            plot += "                                         '' using ($0+" + str(x) + "+0.20):3     with lines lc rgb 'gray'         title '', "

        self.walk_tree_leaf_set(testmeta, data_drops)
        self.plotutils.gpi += """
            plot """ + plot + """
            unset multiplot"""

        self.plotutils.generate(outfile)


class Plot():
    gpi = ''
    size = '21cm,10cm'

    def generate(self, outputFile):
        self.gpi = """
            reset
            set terminal pdfcairo font 'Times-Roman,12' size """ + self.size + """
            set output '""" + outputFile + """.pdf'
            """ + self.gpi

        self.gpi = re.sub(r'^[\t ]+', '', self.gpi, 0, re.MULTILINE)

        with open(outputFile + '.gpi', 'w') as f:
            f.write(self.gpi)

        local['gnuplot'][outputFile + '.gpi'].run(stdin=None, stdout=None, stderr=None, retcode=None)

        self.gpi = ''

    def header(self, num=1):
        self.gpi += """
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
        hp = HierarchyPlot()
        hp.plot(folder + '/analysis_compare', {
            'title': folder,
            #'xlabel': 'something',
            'children': [{'testcase': x} for x in testfolders]
        })

    def plot_multiple_flows(self, testfolders, output_path):
        """Generate a PDF with one page with graphs per flow"""

        for testfolder in testfolders:
            self.plot_flow(testfolder, generate=False)

        self.generate(output_path)

    def plot_flow(self, testfolder, generate=True):
        """Generate a plot for a single test case"""

        self.size = '21cm,30cm'

        n = 0
        flows = {
            'ecn': [],
            'nonecn': []
        }

        for (type, items) in flows.items():
            with open(testfolder + '/flows_' + type, 'r') as f:
                for line in f:
                    items.append(line.strip())
                    n += 1

        self.header()

        self.gpi += """
            set multiplot layout 4,1 columnsfirst title '""" + testfolder + """'
            set lmargin 13
            set yrange [0:]
            set xrange [1:]
            set format y "%g"
            set ylabel 'Utilization in %'
            set style fill transparent solid 0.5 noborder
            set key above
            plot """

        self.gpi += "'" + testfolder + "/util'    using ($0+1):2   with lines lw 1.5 title 'Total utilization', "
        self.gpi += "                       ''    using ($0+1):3   with lines lw 1.5 lc rgb 'red'    title 'ECN utilization', "
        self.gpi += "                       ''    using ($0+1):4   with lines lw 1.5               title 'Non-ECN utilization', "

        self.gpi += """

            set format y "%.0f"
            set ylabel 'Rate [b/s]'
            set key right center inside
            plot 0 title '', """

        for (type, items) in flows.items():
            j = 0
            for flow in items:
                pt = 2 if type == 'ecn' else 6
                ls = 3 if type == 'ecn' else 5
                self.gpi += "'" + testfolder + "/r_pf_" + type + "'    using ($0+1):" + str(3 + j) + ":xtic($2/1000)   with linespoints ls " + str(ls) + " pointtype " + str(pt) + " ps 0.2 lw 1.5    title '" + type + " - " + flow + "', "
                j += 1

        self.gpi += """
            """

        self.header()

        self.gpi += """
            set format y "%g"
            set offset graph 0, graph 0, graph 0.02, graph 0.02
            set ylabel 'Packets per sample'
            set key above
            plot """

        self.gpi += "'" + testfolder + "/d_tot_nonecn'   using ($0+1):3 with linespoints pointtype 7 ps 0.2 lw 1.5 title 'Drops (nonecn)', "
        self.gpi += "'" + testfolder + "/d_tot_ecn'   using ($0+1):3 with linespoints pointtype 7 ps 0.2 lw 1.5 lc rgb 'red' title 'Drops (ecn)', "
        self.gpi += "'" + testfolder + "/m_tot_ecn'   using ($0+1):3 with linespoints pointtype 7 ps 0.2 lw 1.5 title 'Marks (ecn)', "

        self.gpi += """
            set ylabel 'Queueing delay [ms]'
            set xlabel 'Sample'
            plot """

        # old ps: 2 4 6 1 4 6
        self.gpi += "'" + testfolder + "/qs_samples_ecn' using ($0+1):2 with linespoints pointtype 7 ps 0.2 lw 1.5 title 'Max (ECN)', "
        self.gpi +=                                  "'' using ($0+1):5 with linespoints pointtype 7 ps 0.2 lw 1.5 title '99th percentile (ECN)', "
        self.gpi +=                                  "'' using ($0+1):3 with linespoints pointtype 7 ps 0.2 lw 1.5 title 'Average (ECN)', "
        self.gpi += "'" + testfolder + "/qs_samples_nonecn' using ($0+1):2 with linespoints pointtype 7 ps 0.2 lw 1.5 title 'Max (Non-ECN)', "
        self.gpi +=                                     "'' using ($0+1):5 with linespoints pointtype 7 ps 0.2 lw 1.5 title '99th percentile (Non-ECN)', "
        self.gpi +=                                     "'' using ($0+1):3 with linespoints pointtype 7 ps 0.2 lw 1.5 title 'Average (Non-ECN)', "

        self.gpi += """
            unset multiplot"""

        if generate:
            self.generate(testfolder + '/analysis')

    def getTag(self, testcase):
        with open(testcase['testcase'] + '/details', 'r') as f:
            for line in f:
                if line.startswith('x_udp_rate'):
                    return str(int(int(line.split()[1]) / 1000))
                elif line.startswith('xlabel '):
                    return line.split(maxsplit=1)[1].strip()

        return 'n/a'

    def mergeTestcaseData(self, testcases, statsname):
        out = []
        for testcase in testcases:
            with open(testcase['testcase'] + '/' + statsname, 'r') as f:
                tag = self.getTag(testcase)

                for line in f:
                    if line.startswith('#'):
                        continue

                    out.append(tag + ' ' + line)

        return ''.join(out)


def getTestcasesInFolder(folder):
    testcases = []

    for file in os.listdir(folder):
        if file.startswith('test-') and os.path.isdir(os.path.join(folder, file)):
            testcases.append(os.path.join(folder, file))

    return sorted(testcases)


def generateHierarchyData(folderspec, title, xlabel=''):
    """Generate a dict that can be sent to HierarchyPlot"""

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
                node['children'] = [{'testcase': x} for x in getTestcasesInFolder(value)]

    add_level(root, folderspec)
    return root


class TestPlots(unittest.TestCase):

    def testGenerateHierarchyData():
        data = generateHierarchyData({
            'traffic both machines': 'testset-plot-testdata/traffic-ab',
            'traffic only a': 'testset-plot-testdata/traffic-a',
            'traffic only b': 'testset-plot-testdata/traffic-b',
        }, title='Plot testing', xlabel='RTT')

        hp = HierarchyPlot()
        hp.plot('testset-plot-testdata/analysis', data)


if __name__ == '__main__':
    plot = Plot()

    if False:
        data = generateHierarchyData({
            '1 flow each': {
                'cubic vs cubic': 'testset-simple/flows-1/cubic',
                'cubic vs cubic-ecn': 'testset-simple/flows-1/cubic-ecn',
                'cubic vs dctcp': 'testset-simple/flows-1/cubic-dctcp',
            },
            '2 flow each': {
                'cubic vs cubic': 'testset-simple/flows-2/cubic',
                'cubic vs cubic-ecn': 'testset-simple/flows-2/cubic-ecn',
                'cubic vs dctcp': 'testset-simple/flows-2/cubic-dctcp',
            },
            '3 flow each': {
                'cubic vs cubic': 'testset-simple/flows-3/cubic',
                'cubic vs cubic-ecn': 'testset-simple/flows-3/cubic-ecn',
                'cubic vs dctcp': 'testset-simple/flows-3/cubic-dctcp',
            },
        }, title='Testing cubic vs different flows', xlabel='RTT')

        hp = HierarchyPlot()
        hp.plot('testset-simple/test1', data)

    if False:
        plot.plot_flow('testset-speeds/nonect/test-001')

    if True:
        data = generateHierarchyData({
            'UDP with Non-ECT': 'testset-speeds/nonect',
            'UDP with ECT(1)': 'testset-speeds/ect1'
        }, title='Overload with UDP', xlabel='UDP bitrate [kbps]')

        hp = HierarchyPlot()
        hp.plot('testset-speeds/analysis', data)

    if True:
        for subfolder in ['nonect', 'ect1']:
            folder = 'testset-speeds/' + subfolder
            plot.plot_multiple_flows(getTestcasesInFolder(folder), folder + '/analysis_combined')
