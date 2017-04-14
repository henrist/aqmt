from collections import OrderedDict


def utilization_queue(y_logarithmic=False):
    def plot(testfolder):

        gpi = """
            set yrange [0:]
            set format y "%g"
            set ylabel 'Utilization per queue [%]'
            set style fill transparent solid 0.5 noborder
            set key above
        """

        if y_logarithmic:
            gpi += """
                set logscale y
                set yrange [1000:]
            """
        else:
            gpi += """
                set yrange [0:]
            """

        gpi += """

            set style line 100 lt 1 lc rgb 'black' lw 1.5 dt 3
            set arrow 100 from graph 0, first 100 to graph 1, first 100 nohead ls 100 back

            stats '""" + testfolder + """/derived/util_tagged' using 1 nooutput
            plot \\
        """

        #ls 1 lw 1.5 lc variable
        gpi += "'" + testfolder + "/derived/util'    using ($0+1):($2*100)   with lines ls 1 lw 1.5 title 'Total utilization', \\\n"
        gpi += "''                                   using ($0+1):($3*100)   with lines ls 2 lw 1.5 title 'ECN utilization', \\\n"
        gpi += "''                                   using ($0+1):($4*100)   with lines ls 3 lw 1.5 title 'Non-ECN utilization', \\\n"

        gpi += "for [IDX=0:STATS_blocks-1] '" + testfolder + "/derived/util_tagged' index IDX using ($1+1):($2*100) with lines ls (IDX+3) title columnheader(1), \\\n"

        gpi += """
            unset arrow 100
            unset logscale y
        """

        return gpi

    return plot


def rate_per_flow(y_logarithmic=False):
    def plot(testfolder):

        n_flows = 0
        flows = OrderedDict({
            'ecn': [],
            'nonecn': []
        })

        for ecntype, items in flows.items():
            with open(testfolder + '/ta/flows_' + ecntype, 'r') as f:
                for line in f:
                    items.append(line.strip())
                    n_flows += 1

        gpi = """
            set format y "%.0f"
            set ylabel 'Rate per flow [b/s]'
            set key right center inside
        """

        if y_logarithmic:
            gpi += """
                set logscale y
                set yrange [1000:]
            """
        else:
            gpi += """
                set yrange [0:]
            """

        gpi += """
            plot \\
            """

        if n_flows == 0:
            gpi += "0 title '',"

        for type, items in flows.items():
            j = 0
            for flow in items:
                pt = 2 if type == 'ecn' else 6
                ls = 2 if type == 'ecn' else 3
                gpi += "'" + testfolder + "/ta/r_pf_" + type + "'    using ($0+1):" + str(3 + j) + ":xtic($2/1000)   with linespoints ls " + str(ls) + " pointtype " + str(pt) + " ps 0.2 lw 1.5    title '" + type + " - " + flow + "', \\\n"
                j += 1

        gpi += """
            unset logscale y
        """

        return gpi

    return plot


def queuedelay(y_logarithmic=False):
    def plot(testfolder):
        gpi = """
            set ylabel "Queueing delay per queue [ms]\\n{/Times:Italic=10 (min, p_{25}, mean, p_{99}, max)}"
            unset bars
            set key above
            set xtics out nomirror
        """

        if y_logarithmic:
            gpi += """
                set logscale y
                set yrange [1:]
            """
        else:
            gpi += """
                set yrange [0:]
            """

        gpi += """
            plot \\
            """

        # 1=sample_id 2=min 3=p25 4=average 5=p99 6=max
        #             4     6     2         9    10
        gpi += "'" + testfolder + "/derived/qs_samples_ecn' using ($0+0.95):($2/1000):($4/1000):($9/1000) with yerrorbars ls 2 pointtype 7 ps 0.3 lw 1.5 title 'ECN packets', \\\n"
        gpi += "''                                          using ($0+0.95):($2/1000) with lines lc rgb 'gray'         title '', \\\n"
        gpi += "''                                          using ($0+0.95):($10/1000) with points  ls 2 pointtype 1 ps 0.3 lw 1.5 title '', \\\n"
        gpi += "''                                          using ($0+0.95):($6/1000) with points  ls 2 pointtype 1 ps 0.3 lw 1.5 title '', \\\n"
        gpi += "'" + testfolder + "/derived/qs_samples_nonecn' using ($0+1.05):($2/1000):($4/1000):($9/1000) with yerrorbars ls 3 pointtype 7 ps 0.3 lw 1.5 title 'Non-ECN packets', \\\n"
        gpi += "''                                             using ($0+1.05):($2/1000) with lines lc rgb 'gray'         title '', \\\n"
        gpi += "''                                             using ($0+1.05):($10/1000) with points  ls 3 pointtype 1 ps 0.3 lw 1.5 title '', \\\n"
        gpi += "''                                             using ($0+1.05):($6/1000) with points  ls 3 pointtype 1 ps 0.3 lw 1.5 title '', \\\n"

        gpi += """
            unset logscale y
        """

        return gpi

    return plot


def drop_marks(y_logarithmic=False):
    def plot(testfolder):
        gpi = """
            set format y "%g"
            set ylabel "Packets per sample\\n{/Times:Italic=10 Dotted lines are max packets in the queue}"
            set bars
        """

        if y_logarithmic:
            gpi += """
                set logscale y
                set yrange [1:]
            """
        else:
            gpi += """
                set yrange [0:]
            """

        gpi += """
            set xtics in mirror
            set key above
            plot \\
        """

        gpi += "'" + testfolder + "/ta/d_tot_ecn'   using ($0+1):3 with linespoints pointtype 7 ps 0.2 lw 1.5 lc rgb 'red' title 'Drops (ECN)', \\\n"
        gpi += "'" + testfolder + "/ta/m_tot_ecn'   using ($0+1):3 with linespoints ls 8 pointtype 7 ps 0.2 lw 1.5 title 'Marks (ECN)', \\\n"
        gpi += "'" + testfolder + "/ta/d_tot_nonecn'   using ($0+1):3 with linespoints ls 3 pointtype 7 ps 0.2 lw 1.5 title 'Drops (Non-ECN)', \\\n"

        #gpi += "'" + testfolder + "/ta/tot_packets_ecn'   using ($0+1):1 with linespoints ls 8 dt 3 pointtype 7 ps 0.2 lw 1.5 title '', \\\n"
        #gpi += "'" + testfolder + "/ta/tot_packets_nonecn'   using ($0+1):1 with linespoints ls 3 dt 3 pointtype 7 ps 0.2 lw 1.5 title '', \\\n"

        gpi += """
            unset logscale y
        """

        return gpi

    return plot
