#!/usr/bin/env python3
from plumbum import local
import os.path
import re

color_cubic = "#FC6C6C"
color_dctcp = "blue"
color_udp_l4s = "purple"
color_ecn_cubic = "black"
color_reno = "brown"
color_util = "orange"

class Plot():
    gpi = ''
    size = '21cm,10cm'

    def generate(self, outputFile):
        self.gpi = """
            #reset
            set terminal pdfcairo font 'Times-Roman,12' size """ + self.size + """
            set output '""" + outputFile + """.pdf'""" + self.gpi

        self.gpi = re.sub(r'^[\t ]+', '', self.gpi, 0, re.MULTILINE)

        with open(outputFile + '.gpi', 'w') as f:
            f.write(self.gpi)

        local['gnuplot'][outputFile + '.gpi']()

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

            #set label 2 'RTT[ms]:' at screen 0.25,0.6 front font 'Times-Roman,120' tc rgb 'black' left
            #set label 30 'PI2' at screen 1,3.4 font 'Times-Roman,140' tc rgb 'black' left"""


    def plot_compare_flows(self, folder, testfolders):
        local['./merge.sh'][folder, testfolders]()

        num = int((local['wc']['-l', folder + '/util_stats'] | local['awk']['{print $1-1}'])())

        self.size = '21cm,22cm'
        self.header(num=num)

        self.gpi += """
            set multiplot layout 3,1

            set title '""" + folder + """'
            set xrange [-.6:""" + str(num-1) + """.9]
            set yrange [0:]
            set boxwidth 0.2
            set lmargin 13"""


        self.gpi += """

            #set style line 100 lt 1 lc rgb 'red' lw 2
            #set arrow 100 from 1,-1 to 1,1 nohead ls 100 front
            #set arrow 100 from graph 0, second 100 to graph 1, second 100 nohead ls 100 front

            set xtic offset first .3
            set ylabel 'Percent (p1, mean, p99)'

            plot """

        self.gpi += "'" + folder + "/util_stats'      using ($0+0):3:5:4:xtic(1)       with yerrorbars pointtype 7 pointsize 0.5 lw 1.5 title 'Total utilization', "
        self.gpi += "                              '' using ($0+0.0):3  with lines lc rgb 'gray'         title '', "
        self.gpi += "                         ''      using ($0+0.1):6:8:7:xtic('')    with yerrorbars pointtype 7 pointsize 0.5 lw 1.5 title 'ECN utilization', "
        self.gpi += "                              '' using ($0+0.1):6  with lines lc rgb 'gray'         title '', "
        self.gpi += "                         ''      using ($0+0.2):9:10:11:xtic('')  with yerrorbars pointtype 7 pointsize 0.5 lw 1.5 title 'Non-ECN utilization', "
        self.gpi += "                              '' using ($0+0.2):9  with lines lc rgb 'gray'         title '', "


        self.gpi += """
            set ylabel 'Queueing delay [ms]'
            set xtic offset first .15

            plot """

        self.gpi += "'" + folder + "/qs_ecn_stats'    using ($0+0.05):3:5:4:xtic(1)   with yerrorbars pointtype 7 pointsize 0.5 lw 1.5            title 'L4S queue', "
        self.gpi += "                              '' using ($0+0.05):3  with lines lc rgb 'gray'         title '', "
        self.gpi += "'" + folder + "/qs_nonecn_stats' using ($0+0.15):3:5:4  with yerrorbars pointtype 7 pointsize 0.5 lw 1.5           title 'Classic queue', "
        self.gpi += "                              '' using ($0+0.15):3  with lines lc rgb 'gray'         title '', "

        self.gpi += """
            set xtic offset first .15
            set ylabel 'Percent (p1, mean, p99)'
            set xlabel 'UDP bitrate [kbps]'

            plot """

        self.gpi += "'" + folder + "/d_percent_nonecn_stats'  using ($0+0.0):3:5:4:xtic(1) with yerrorbars pointtype 7 pointsize 0.5 lw 1.5  title 'Drops (nonecn)', "
        #self.gpi += "                                      '' using ($0+0.0):3  with lines lc rgb 'gray'         title '', "
        self.gpi += "'" + folder + "/d_percent_ecn_stats'     using ($0+0.10):3:5:4:xtic('') with yerrorbars pointtype 7 pointsize 0.5 lw 1.5 lc rgb 'red'  title 'Drops (ecn)', "
        #self.gpi += "                                      '' using ($0+0.10):3  with lines lc rgb 'gray'         title '', "
        self.gpi += "'" + folder + "/m_percent_ecn_stats'     using ($0+0.20):3:5:4:xtic('') with yerrorbars pointtype 7 pointsize 0.5 lw 1.5  title 'Marks (ecn)', "
        #self.gpi += "                                      '' using ($0+0.20):3  with lines lc rgb 'gray'         title '', "

        self.gpi += """
            unset multiplot"""

        self.generate(folder + '/analysis_compare')


    def plot_multiple_flows(self, testfolders, output_path):
        #self.gpi += """
        #    set multiplot layout 4,""" + str(len(testfolders)) + """ columnsfirst"""

        for testfolder in testfolders:
            self.plot_flow(testfolder, generate=False)

        #self.gpi += """
        #    unset multiplot"""

        self.generate(output_path)

    def plot_flow(self, testfolder, generate=True):
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

        self.gpi += """
            reset
            set multiplot layout 4,1 columnsfirst title '""" + testfolder + """'"""

        self.header()

        self.gpi += """

            set lmargin 13
            set yrange [0:]
            set xrange [1:]
            set format y "%g"
            set ylabel 'Utilization in %'
            set style fill transparent solid 0.5 noborder
            plot """

        self.gpi += "'" + testfolder + "/util'    using ($0+1):2   with lines lw 2 title 'Total utilization', "
        self.gpi += "                       ''    using ($0+1):3   with lines lw 2 lc rgb 'red'    title 'ECN utilization', "
        self.gpi += "                       ''    using ($0+1):4   with lines lw 2               title 'Non-ECN utilization', "

        self.gpi += """

            set format y "%.0f"
            set ylabel 'Rate [b/s]'
            plot 2 title '', """

        for (type, items) in flows.items():
            j = 0
            for flow in items:
                pt = 2 if type == 'ecn' else 6
                self.gpi += "'" + testfolder + "/r_pf_" + type + "'    using ($0+1):" + str(3 + j) + ":xtic($2/1000)   with linespoints pointtype " + str(pt) + " lw 1.5    title '" + type + " - " + flow + "', "
                j += 1

        self.gpi += """
            """

        self.header(2)

        self.gpi += """

            set format y "%g"
            set offset graph 0, graph 0, graph 0.02, graph 0.02
            set ylabel 'Packets per sample'
            plot """

        self.gpi += "'" + testfolder + "/d_tot_nonecn'   using ($0+1):3 with linespoints pointtype 4 lw 1.5 title 'Drops (nonecn)', "
        self.gpi += "'" + testfolder + "/d_tot_ecn'   using ($0+1):3 with linespoints pointtype 2 lw 1.5 lc rgb 'red' title 'Drops (ecn)', "
        self.gpi += "'" + testfolder + "/m_tot_ecn'   using ($0+1):3 with linespoints pointtype 6 lw 1.5 title 'Marks (ecn)', "

        self.gpi += """
            set ylabel 'Queueing delay [ms]'
            set xlabel 'Sample'
            plot """

        self.gpi += "'" + testfolder + "/qs_samples_ecn' using ($0+1):2 with linespoints pointtype 2 ps 1 lw 1.5 title 'Max (ECN)', "
        self.gpi +=                                  "'' using ($0+1):5 with linespoints pointtype 4 lw 1.5 title '99th percentile (ECN)', "
        self.gpi +=                                  "'' using ($0+1):3 with linespoints pointtype 6 lw 1.5 title 'Average (ECN)', "
        self.gpi += "'" + testfolder + "/qs_samples_nonecn' using ($0+1):2 with linespoints pointtype 1 ps 1 lw 1.5 title 'Max (Non-ECN)', "
        self.gpi +=                                     "'' using ($0+1):5 with linespoints pointtype 4 lw 1.5 title '99th percentile (Non-ECN)', "
        self.gpi +=                                     "'' using ($0+1):3 with linespoints pointtype 6 lw 1.5 title 'Average (Non-ECN)', "

        self.gpi += """
            unset multiplot"""

        if generate:
            #self.gpi += """
            #    unset multiplot"""

            self.generate(testfolder + '/analysis')

if __name__ == '__main__':
    plot = Plot()

    if False:
        plot.plot_flow('testset-speeds/test-001')

    if False:
        plot.plot_flow('tesetset-a/test-001')
        plot.plot_multiple_flows([
            'testset-a/test-001',
            'testset-a/test-002',
            'testset-a/test-003'],
            'testset-a/analysis')


    if True:
        plot.plot_compare_flows('testset-speeds/nonect', [
            'testset-speeds/nonect/test-001',
            'testset-speeds/nonect/test-002',
            'testset-speeds/nonect/test-003',
            'testset-speeds/nonect/test-004',
            'testset-speeds/nonect/test-005',
            'testset-speeds/nonect/test-006',
            'testset-speeds/nonect/test-007',
            'testset-speeds/nonect/test-008',
            'testset-speeds/nonect/test-009',
            'testset-speeds/nonect/test-010',
            'testset-speeds/nonect/test-011',
            'testset-speeds/nonect/test-012',
            'testset-speeds/nonect/test-013',
            'testset-speeds/nonect/test-014',
            'testset-speeds/nonect/test-015',
            'testset-speeds/nonect/test-016',
            'testset-speeds/nonect/test-017'])
