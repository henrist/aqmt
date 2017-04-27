from collections import OrderedDict
from .common import add_plot, add_scale


def utilization_queues():
    y_logarithmic = False

    """
    Plot utilization per queue

    We do not support logarithmic scale as we are using 'stats'
    command in gnuplot that don't support it.
    """

    def plot(testfolder):
        gpi = """
            set format y "%g"
            set ylabel 'Utilization per queue [%]'
            set style fill transparent solid 0.5 noborder
            set key above
            """ + add_scale(y_logarithmic, range_from_log='1000', range_to='100<*') + """

            set style line 100 lt 1 lc rgb 'black' lw 1.5 dt 3
            set arrow 100 from graph 0, first 100 to graph 1, first 100 nohead ls 100 back

            set label "Sample #:" at graph -0.01, graph -.05 font 'Times-Roman,11pt' tc rgb 'black' right

            stats '""" + testfolder + """/derived/util_tagged' using 1 nooutput
            """

        # add hidden line to force autoscaling if using logarithimic plot without any points
        plot_gpi = " 1 lc rgb '#FFFF0000' notitle, \\\n"

        #ls 1 lw 1.5 lc variable
        plot_gpi += "'" + testfolder + "/derived/util'    using ($0+1):($2*100)   with lines ls 1 lw 1.5 title 'Total utilization', \\\n"
        plot_gpi += "''                                   using ($0+1):($3*100)   with lines ls 2 lw 1.5 title 'ECN utilization', \\\n"
        plot_gpi += "''                                   using ($0+1):($4*100)   with lines ls 3 lw 1.5 title 'Non-ECN utilization', \\\n"

        plot_gpi += "for [IDX=0:STATS_blocks-1] '" + testfolder + "/derived/util_tagged' index IDX using ($1+1):($2*100) with lines ls (IDX+3) title columnheader(1), \\\n"

        gpi += """
            plot \\
            """ + add_plot(plot_gpi) + """

            unset label
            unset arrow 100
            unset logscale y
            """

        return {
            'gpi': gpi,
        }

    return plot


def rate_per_flow(y_logarithmic=False):
    def plot(testfolder):
        flows = OrderedDict({
            'ecn': [],
            'nonecn': []
        })

        for ecntype, items in flows.items():
            with open(testfolder + '/ta/flows_' + ecntype, 'r') as f:
                for line in f:
                    items.append(line.strip())

        gpi = """
            set format y "%.0f"
            set ylabel 'Rate per flow [b/s]'
            set key right center inside
            """ + add_scale(y_logarithmic, range_from_log='1000', range_to='10000<*') + """
            set label "Sample #:" at graph -0.01, graph -.05 font 'Times-Roman,11pt' tc rgb 'black' right
            """

        # add hidden line to force autoscaling if using logarithimic plot without any points
        plot_gpi = " 1 lc rgb '#FFFF0000' notitle, \\\n"

        for type, items in flows.items():
            j = 0
            for flow in items:
                pt = 2 if type == 'ecn' else 6
                ls = 2 if type == 'ecn' else 3
                plot_gpi += "'" + testfolder + "/ta/flows_rate_" + type + "'    using ($0+1):" + str(3 + j) + ":xtic($2/1000)   with linespoints ls " + str(ls) + " pointtype " + str(pt) + " ps 0.2 lw 1.5    title '" + type + " - " + flow + "', \\\n"
                j += 1

        gpi += """
            plot \\
            """ + add_plot(plot_gpi) + """

            unset label
            unset logscale y
            """

        return {
            'gpi': gpi,
        }

    return plot


def queueing_delay(y_logarithmic=False):
    def plot(testfolder):
        gpi = """
            set ylabel "Queueing delay per queue [ms]\\n{/Times:Italic=10 (min, p_{25}, mean, p_{99}, max)}"
            unset bars
            set key above
            set xtics out nomirror
            """ + add_scale(y_logarithmic, range_from_log='0.1', range_to='5<*') + """
            set label "Sample #:" at graph -0.01, graph -.05 font 'Times-Roman,11pt' tc rgb 'black' right
            """

        # add hidden line to force autoscaling if using logarithimic plot without any points
        plot_gpi = " 1 lc rgb '#FFFF0000' notitle, \\\n"

        # 1=sample_id 2=min 3=p25 4=average 5=p99 6=max
        #             4     6     2         9    10
        plot_gpi += "'" + testfolder + "/derived/queue_ecn_samplestats' using ($0+0.95):($2/1000):($4/1000):($9/1000) with yerrorbars ls 2 pointtype 7 ps 0.3 lw 1.5 title 'ECN packets', \\\n"
        plot_gpi += "''                                          using ($0+0.95):($2/1000) with lines lc rgb 'gray'         title '', \\\n"
        plot_gpi += "''                                          using ($0+0.95):($10/1000) with points  ls 2 pointtype 1 ps 0.3 lw 1.5 title '', \\\n"
        plot_gpi += "''                                          using ($0+0.95):($6/1000) with points  ls 2 pointtype 1 ps 0.3 lw 1.5 title '', \\\n"
        plot_gpi += "'" + testfolder + "/derived/queue_nonecn_samplestats' using ($0+1.05):($2/1000):($4/1000):($9/1000) with yerrorbars ls 3 pointtype 7 ps 0.3 lw 1.5 title 'Non-ECN packets', \\\n"
        plot_gpi += "''                                             using ($0+1.05):($2/1000) with lines lc rgb 'gray'         title '', \\\n"
        plot_gpi += "''                                             using ($0+1.05):($10/1000) with points  ls 3 pointtype 1 ps 0.3 lw 1.5 title '', \\\n"
        plot_gpi += "''                                             using ($0+1.05):($6/1000) with points  ls 3 pointtype 1 ps 0.3 lw 1.5 title '', \\\n"

        gpi += """
            plot \\
            """ + add_plot(plot_gpi) + """

            unset label
            unset logscale y
            """

        return {
            'gpi': gpi,
        }

    return plot


def drops_marks(y_logarithmic=False):
    def plot(testfolder):
        gpi = """
            set format y "%g"
            set ylabel "Packets per sample\\n{/Times:Italic=10 Dotted lines are max packets in the queue}"
            set bars
            set xtics in mirror
            set key above
            """ + add_scale(y_logarithmic, range_to='10<*') + """
            set label "Sample #:" at graph -0.01, graph -.05 font 'Times-Roman,11pt' tc rgb 'black' right
            """

        # add hidden line to force autoscaling if using logarithimic plot without any points
        plot_gpi = " 1 lc rgb '#FFFF0000' notitle, \\\n"

        plot_gpi += "'" + testfolder + "/ta/drops_ecn'   using ($0+1):3 with linespoints pointtype 7 ps 0.2 lw 1.5 lc rgb 'red' title 'Drops (ECN)', \\\n"
        plot_gpi += "'" + testfolder + "/ta/marks_ecn'   using ($0+1):3 with linespoints ls 8 pointtype 7 ps 0.2 lw 1.5 title 'Marks (ECN)', \\\n"
        plot_gpi += "'" + testfolder + "/ta/drops_nonecn'   using ($0+1):3 with linespoints ls 3 pointtype 7 ps 0.2 lw 1.5 title 'Drops (Non-ECN)', \\\n"

        #plot_gpi += "'" + testfolder + "/ta/packets_ecn'   using ($0+1):1 with linespoints ls 8 dt 3 pointtype 7 ps 0.2 lw 1.5 title '', \\\n"
        #plot_gpi += "'" + testfolder + "/ta/packets_nonecn'   using ($0+1):1 with linespoints ls 3 dt 3 pointtype 7 ps 0.2 lw 1.5 title '', \\\n"

        gpi += """
            plot \\
            """ + add_plot(plot_gpi) + """

            unset label
            unset logscale y
            """

        return {
            'gpi': gpi,
        }

    return plot


def window(y_logarithmic=False):
    def plot(testfolder):
        gpi = """
            set format y "%g"
            set ylabel "Estimated window size\\n{/Times:Italic=10 [1500 B]}"
            set bars
            set xtics in mirror
            set key above
            """ + add_scale(y_logarithmic, range_to='10<*') + """
            set label "Sample #:" at graph -0.01, graph -.05 font 'Times-Roman,11pt' tc rgb 'black' right
            """

        # add hidden line to force autoscaling if using logarithimic plot without any points
        plot_gpi = " 1 lc rgb '#FFFF0000' notitle, \\\n"

        # line format: sample_id window_ecn_in_bits window_nonecn_in_bits
        plot_gpi += "'" + testfolder + "/derived/window'   using ($0+1):($2/1500/8) with linespoints      pointtype 7 ps 0.2 lw 1.5 lc rgb 'red' title 'ECN', \\\n"
        plot_gpi += "'" + testfolder + "/derived/window'   using ($0+1):($3/1500/8) with linespoints ls 3 pointtype 7 ps 0.2 lw 1.5              title 'Non-ECN', \\\n"

        gpi += """
            plot \\
            """ + add_plot(plot_gpi) + """

            unset label
            unset logscale y
            """

        return {
            'gpi': gpi,
        }

    return plot
