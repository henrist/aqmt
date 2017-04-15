from .collection import get_tmargin_base, is_custom_xtics
from .common import add_plot, add_scale
from . import collectionutil
from . import treeutil
from . import colors


def utilization_queues(y_logarithmic=False):
    """
    Plot graph of utilization for total, ECN and non-ECN flows
    """

    def plot(tree, x_axis, leaf_hook):

        gpi = """
            # utilization
            set style line 100 lt 1 lc rgb 'black' lw 1.5 dt 3
            set arrow 100 from graph 0, first 100 to graph 1, first 100 nohead ls 100 back

            set ylabel "Utilization per queue [%]\\n{/Times:Italic=10 (p_1, mean, p_{99})}"
            """ + add_scale(y_logarithmic, range_from_log='0.1', range_to='*<105', range_to_log='105')

        if is_custom_xtics(x_axis):
            gpi += """
                # add xtics below, the empty list resets the tics
                set xtics ()
                """

        # add hidden line to force autoscaling if using logarithimic plot without any points
        plot_gpi = " 1 lc rgb '#FFFF0000' notitle, \\\n"

        def leaf(subtree, is_first_set, x):
            nonlocal plot_gpi, gpi
            leaf_hook(subtree, is_first_set, x)

            xtics = ":xtic(2)"
            if is_custom_xtics(x_axis):
                xtics = ""
                gpi += """
                    set xtics add (""" + collectionutil.make_xtics(subtree, x, x_axis) + """)
                    """

            gpi += """
                $data_util""" + str(x) + """ << EOD
                """ + collectionutil.merge_testcase_data(subtree, 'aggregated/util_stats', x_axis) + """
                EOD
                $data_util_ecn""" + str(x) + """ << EOD
                """ + collectionutil.merge_testcase_data(subtree, 'aggregated/util_ecn_stats', x_axis) + """
                EOD
                $data_util_nonecn""" + str(x) + """ << EOD
                """ + collectionutil.merge_testcase_data(subtree, 'aggregated/util_nonecn_stats', x_axis) + """
                EOD"""

            # total
            plot_gpi += "$data_util" + str(x) + "        using ($1+" + str(x) + "+0.0):3:10:6" + xtics + "       with yerrorbars ls 1 pointtype 7 pointsize 0.4 lc rgb '" + colors.AGGR + "' lw 1.5 title '" + ('Total utilization' if is_first_set else '') + "', \\\n"
            #plot_gpi += "''                              using ($1+" + str(x) + "+0.0):7  with points  ls 1 pointtype 1 pointsize 0.4        title '', \\\n"
            #plot_gpi += "''                              using ($1+" + str(x) + "+0.0):9  with points  ls 1 pointtype 1 pointsize 0.4        title '', \\\n"
            plot_gpi += "''                              using ($1+" + str(x) + "+0.0):3  with lines lc rgb 'gray'         title '', \\\n" # gray lines total, ecn, nonecn

            # ecn
            plot_gpi += "$data_util_ecn" + str(x) + "  using ($1+" + str(x) + "+0.1):3:10:6    with yerrorbars ls 2 pointtype 7 pointsize 0.4 lc rgb '" + colors.L4S + "' lw 1.5 title '" + ('ECN utilization' if is_first_set else '') + "', \\\n"
            #plot_gpi += "''                            using ($1+" + str(x) + "+0.1):7   with points  ls 2 pointtype 1 pointsize 0.4        title '', \\\n"
            #plot_gpi += "''                            using ($1+" + str(x) + "+0.1):9  with points  ls 2 pointtype 1 pointsize 0.4        title '', \\\n"
            plot_gpi += "''                            using ($1+" + str(x) + "+0.1):3  with lines lc rgb 'gray'         title '', \\\n" # gray lines total, ecn, nonecn

            # nonecn
            plot_gpi += "$data_util_nonecn" + str(x) + "  using ($1+" + str(x) + "+0.2):3:10:5  with yerrorbars ls 3 pointtype 7 pointsize 0.4 lc rgb '" + colors.CLASSIC + "' lw 1.5 title '" + ('Non-ECN utilization' if is_first_set else '') + "', \\\n"
            #plot_gpi += "''                               using ($1+" + str(x) + "+0.2):7  with points  ls 3 pointtype 1 pointsize 0.4        title '', \\\n"
            #plot_gpi += "''                               using ($1+" + str(x) + "+0.2):9  with points  ls 3 pointtype 1 pointsize 0.4        title '', \\\n"
            plot_gpi += "''                               using ($1+" + str(x) + "+0.2):3  with lines lc rgb 'gray'         title '', \\\n" # gray lines total, ecn, nonecn

        treeutil.walk_leaf(tree, leaf)
        gpi += """
            plot \\
            """ + add_plot(plot_gpi) + """

            unset arrow 100
            unset logscale y
            """

        return {
            'y_logarithmic': y_logarithmic,
            'gpi': gpi,
        }

    return plot


def utilization_tags(y_logarithmic=False):
    """
    Plot graph of utilization for classified (tagged) traffic
    """

    def plot(tree, x_axis, leaf_hook):
        gpi = """
            # utilization of tags
            set style line 100 lt 1 lc rgb 'black' lw 1.5 dt 3
            set arrow 100 from graph 0, first 100 to graph 1, first 100 nohead ls 100 back

            set ylabel "Utilization of classified traffic [%]\\n{/Times:Italic=10 (p_{25}, mean, p_{75})}"
            """ + add_scale(y_logarithmic, range_from_log='0.1', range_to='*<105', range_to_log='105')

        if is_custom_xtics(x_axis):
            gpi += """
                # add xtics below, the empty list resets the tics
                set xtics ()
                """

        # add hidden line to force autoscaling if using logarithimic plot without any points
        plot_gpi = " 1 lc rgb '#FFFF0000' notitle, \\\n"

        plot_lines = ''
        titles_used = []

        def leaf(subtree, is_first_set, x):
            nonlocal plot_gpi, plot_lines, gpi, titles_used
            leaf_hook(subtree, is_first_set, x)

            xtics = ":xtic(2)"
            if is_custom_xtics(x_axis):
                xtics = ""
                gpi += """
                    set xtics add (""" + collectionutil.make_xtics(subtree, x, x_axis) + """)
                    """

            gpi += """
                $dataUtil""" + str(x) + """ << EOD
                """ + collectionutil.merge_testcase_data(subtree, 'aggregated/util_stats', x_axis) + """
                EOD"""

            # total
            plot_gpi += "$dataUtil" + str(x) + "  using ($1+" + str(x) + "+0.0):3:9:7" + xtics + "       with yerrorbars ls 1 pointtype 7 pointsize 0.4 lc rgb '" + colors.AGGR + "' lw 1.5 title '" + ('Total utilization' if is_first_set else '') + "', \\\n"
            plot_lines += "$dataUtil" + str(x) + "  using ($1+" + str(x) + "+0.0):3  with lines lc rgb 'gray'         title '', \\\n"

            tagged_flows = collectionutil.merge_testcase_data_group(subtree, 'aggregated/util_tagged_stats', x_axis)
            x_distance = .4 / len(tagged_flows)

            for i, (tagname, data) in enumerate(tagged_flows.items()):
                gpi += """
                    $dataUtil""" + str(x) + "_" + str(i) + """ << EOD
                    """ + data + """
                    EOD"""

                if tagname in titles_used:
                    title = ''
                else:
                    titles_used.append(tagname)
                    title = tagname

                plot_gpi += "$dataUtil" + str(x) + "_" + str(i) + "  using ($1+" + str(x+((i+1) * x_distance)) + "):($4*100):($10*100):($8*100)       with yerrorbars ls 1 pointtype 7 pointsize 0.4 lc rgb '" + colors.get_from_tagname(tagname) + "' lw 1.5 title '" + title + "', \\\n"
                plot_lines += "$dataUtil" + str(x) + "_" + str(i) + "  using ($1+" + str(x+((i+1) * x_distance)) + "):($4*100) with lines lc rgb 'gray' title '', \\\n"

        treeutil.walk_leaf(tree, leaf)

        gpi += """
            set tmargin """ + str(get_tmargin_base(tree) + 1.3 * (len(titles_used)+1) / 4 - 1) + """

            plot \\
            """ + add_plot(plot_gpi + plot_lines) + """

            unset arrow 100
            unset logscale y
            """

        return {
            'y_logarithmic': y_logarithmic,
            'gpi': gpi,
        }

    return plot


def queueing_delay(y_logarithmic=False):
    """
    Plot graph of queueing delay
    """

    def plot(tree, x_axis, leaf_hook):
        gpi = """
            # queueing delay
            set ylabel "Queueing delay per queue [ms]\\n{/Times:Italic=10 (p_1, p_{25}, mean, p_{75}, p_{99})}"
            #set xtic offset first .1
            """ + add_scale(y_logarithmic, range_to='10<*')

        if is_custom_xtics(x_axis):
            gpi += """
                # add xtics below, the empty list resets the tics
                set xtics ()
                """

        # add hidden line to force autoscaling if using logarithimic plot without any points
        plot_gpi = " 1 lc rgb '#FFFF0000' notitle, \\\n"

        def leaf(subtree, is_first_set, x):
            nonlocal gpi, plot_gpi
            leaf_hook(subtree, is_first_set, x)

            xtics = ":xtic(2)"
            if is_custom_xtics(x_axis):
                xtics = ""
                gpi += """
                    set xtics add (""" + collectionutil.make_xtics(subtree, x, x_axis) + """)
                    """

            gpi += """
                $data_queue_ecn_stats""" + str(x) + """ << EOD
                """ + collectionutil.merge_testcase_data(subtree, 'aggregated/queue_ecn_stats', x_axis) + """
                EOD
                $data_queue_nonecn_stats""" + str(x) + """ << EOD
                """ + collectionutil.merge_testcase_data(subtree, 'aggregated/queue_nonecn_stats', x_axis) + """
                EOD"""

            ls_l4s = "ls 1 lc rgb '" + colors.L4S + "'"
            ls_classic = "ls 1 lc rgb '" + colors.CLASSIC + "'"

            plot_gpi += "$data_queue_ecn_stats" + str(x) + "    using ($1+" + str(x) + "+0.05):($3/1000):($7/1000):($9/1000)" + xtics + "   with yerrorbars " + ls_l4s + " lw 1.5 pointtype 7 pointsize 0.4            title '" + ('ECN packets' if is_first_set else '') + "', \\\n"
            plot_gpi += "''                                     using ($1+" + str(x) + "+0.05):($6/1000)  with points  " + ls_l4s + " pointtype 1 pointsize 0.4        title '', \\\n"
            plot_gpi += "''                                     using ($1+" + str(x) + "+0.05):($10/1000)  with points  " + ls_l4s + " pointtype 1 pointsize 0.4        title '', \\\n"
            plot_gpi += "$data_queue_nonecn_stats" + str(x) + " using ($1+" + str(x) + "+0.15):($3/1000):($7/1000):($9/1000)  with yerrorbars " + ls_classic + " lw 1.5 pointtype 7 pointsize 0.4           title '" + ('Non-ECN packets' if is_first_set else '') + "', \\\n"
            plot_gpi += "''                                     using ($1+" + str(x) + "+0.15):($6/1000)  with points " + ls_classic + " pointtype 1 pointsize 0.4        title '', \\\n"
            plot_gpi += "''                                     using ($1+" + str(x) + "+0.15):($10/1000)  with points " + ls_classic + " pointtype 1 pointsize 0.4        title '', \\\n"

            plot_gpi += "$data_queue_ecn_stats" + str(x) + "    using ($1+" + str(x) + "+0.05):($3/1000)  with lines lc rgb 'gray'         title '', \\\n"
            plot_gpi += "$data_queue_nonecn_stats" + str(x) + " using ($1+" + str(x) + "+0.15):($3/1000)  with lines lc rgb 'gray'         title '', \\\n"

        treeutil.walk_leaf(tree, leaf)
        gpi += """
            plot \\
            """ + add_plot(plot_gpi) + """

            unset logscale y
            """

        return {
            'y_logarithmic': y_logarithmic,
            'gpi': gpi,
        }

    return plot


def drops_marks(y_logarithmic=False):
    """
    Plot graph of drop and marks for ECN and non-ECN queues
    """

    def plot(tree, x_axis, leaf_hook):
        gpi = """
            # drops and marks
            set ylabel "Drop/marks per queue [%]\\n{/Times=10 (of total traffic in the queue)}\\n{/Times:Italic=10 (p_1, p_{25}, mean, p_{75}, p_{99})}"
            set xtic offset first 0
            """ + add_scale(y_logarithmic, range_from_log='.1', range_to='1<*')

        if is_custom_xtics(x_axis):
            gpi += """
                # add xtics below, the empty list resets the tics
                set xtics ()
                """

        # add hidden line to force autoscaling if using logarithimic plot without any points
        plot_gpi = " 1 lc rgb '#FFFF0000' notitle, \\\n"

        def leaf(subtree, is_first_set, x):
            nonlocal gpi, plot_gpi
            leaf_hook(subtree, is_first_set, x)

            xtics = ":xtic(2)"
            if is_custom_xtics(x_axis):
                xtics = ""
                gpi += """
                    set xtics add (""" + collectionutil.make_xtics(subtree, x, x_axis) + """)
                    """

            gpi += """
                $data_d_percent_ecn_stats""" + str(x) + """ << EOD
                """ + collectionutil.merge_testcase_data(subtree, 'aggregated/drops_percent_ecn_stats', x_axis) + """
                EOD
                $data_m_percent_ecn_stats""" + str(x) + """ << EOD
                """ + collectionutil.merge_testcase_data(subtree, 'aggregated/marks_percent_ecn_stats', x_axis) + """
                EOD
                $data_d_percent_nonecn_stats""" + str(x) + """ << EOD
                """ + collectionutil.merge_testcase_data(subtree, 'aggregated/drops_percent_nonecn_stats', x_axis) + """
                EOD"""

            plot_gpi += "$data_d_percent_ecn_stats" + str(x) + "     using ($1+" + str(x) + "+0.00):3:7:9" + xtics + " with yerrorbars lc rgb '" + colors.DROPS_L4S + "' pointtype 7 pointsize 0.4 lw 1.5  title '" + ('Drops (ECN)' if is_first_set else '') + "', \\\n"
            plot_gpi += "''                                          using ($1+" + str(x) + "+0.00):6  with points  lc rgb '" + colors.DROPS_L4S + "' pointtype 1 pointsize 0.4        title '', \\\n"
            plot_gpi += "''                                          using ($1+" + str(x) + "+0.00):10  with points  lc rgb '" + colors.DROPS_L4S + "' pointtype 1 pointsize 0.4        title '', \\\n"
            plot_gpi += "$data_m_percent_ecn_stats" + str(x) + "     using ($1+" + str(x) + "+0.10):3:7:9 with yerrorbars lc rgb '" + colors.MARKS_L4S + "' pointtype 7 pointsize 0.4 lw 1.5  title '" + ('Marks (ECN)' if is_first_set else '') + "', \\\n"
            plot_gpi += "''                                          using ($1+" + str(x) + "+0.10):6  with points  lc rgb '" + colors.MARKS_L4S + "' pointtype 1 pointsize 0.4        title '', \\\n"
            plot_gpi += "''                                          using ($1+" + str(x) + "+0.10):10  with points  lc rgb '" + colors.MARKS_L4S + "' pointtype 1 pointsize 0.4        title '', \\\n"
            plot_gpi += "$data_d_percent_nonecn_stats" + str(x) + "  using ($1+" + str(x) + "+0.20):3:7:9 with yerrorbars lc rgb '" + colors.DROPS_CLASSIC + "' pointtype 7 pointsize 0.4 lw 1.5  title '" + ('Drops (Non-ECN)' if is_first_set else '') + "', \\\n"
            plot_gpi += "''                                          using ($1+" + str(x) + "+0.20):6  with points  lc rgb '" + colors.DROPS_CLASSIC + "' pointtype 1 pointsize 0.4        title '', \\\n"
            plot_gpi += "''                                          using ($1+" + str(x) + "+0.20):10  with points  lc rgb '" + colors.DROPS_CLASSIC + "' pointtype 1 pointsize 0.4        title '', \\\n"

            # gray lines between average values
            plot_gpi += "$data_d_percent_ecn_stats" + str(x) + "     using ($1+" + str(x) + "+0.00):3     with lines lc rgb 'gray'         title '', \\\n"
            plot_gpi += "$data_m_percent_ecn_stats" + str(x) + "     using ($1+" + str(x) + "+0.10):3     with lines lc rgb 'gray'         title '', \\\n"
            plot_gpi += "$data_d_percent_nonecn_stats" + str(x) + "  using ($1+" + str(x) + "+0.20):3     with lines lc rgb 'gray'         title '', \\\n"

        treeutil.walk_leaf(tree, leaf)
        gpi += """
            plot \\
            """ + add_plot(plot_gpi) + """

            unset logscale y
            """

        return {
            'y_logarithmic': y_logarithmic,
            'gpi': gpi,
        }

    return plot


def window_rate_ratio(y_logarithmic=False):
    """
    Plot graph of window and rate ratio between ECN and non-ECN queues
    """

    def plot(tree, x_axis, leaf_hook):
        gpi = """
            # window and rate ratio
            set ylabel "Window and rate ratio\\n{/Times:Italic=10 Above 1 is advantage to ECN-flow}"
            set xtic offset first 0

            # line at y 1 (the perfect balance)
            set style line 100 lt 1 lc rgb 'black' lw 1.5 dt 3
            set arrow 100 from graph 0, first 1 to graph 1, first 1 nohead ls 100 back
            """ + add_scale(y_logarithmic, range_from='*<.5', range_from_log='.5', range_to='2<*')

        if is_custom_xtics(x_axis):
            gpi += """
                # add xtics below, the empty list resets the tics
                set xtics ()
                """

        # add hidden line to force autoscaling if using logarithimic plot without any points
        plot_gpi = " 1 lc rgb '#FFFF0000' notitle, \\\n"

        def leaf(subtree, is_first_set, x):
            nonlocal gpi, plot_gpi
            leaf_hook(subtree, is_first_set, x)

            xtics = ":xtic(2)"
            if is_custom_xtics(x_axis):
                xtics = ""
                gpi += """
                    set xtics add (""" + collectionutil.make_xtics(subtree, x, x_axis) + """)
                    """

            gpi += """
                $data_window_ratio""" + str(x) + """ << EOD
                """ + collectionutil.merge_testcase_data(subtree, 'aggregated/ecn_over_nonecn_window_ratio', x_axis) + """
                EOD
                $data_rate_ratio""" + str(x) + """ << EOD
                """ + collectionutil.merge_testcase_data(subtree, 'aggregated/ecn_over_nonecn_rate_ratio', x_axis) + """
                EOD
                """

            plot_gpi += "$data_window_ratio" + str(x) + "  using ($1+" + str(x) + "+0.00):3" + xtics + " with points lc rgb '" + colors.BLACK + "' pointtype 7 pointsize 0.4 lw 1.5  title '" + ('Window ratio' if is_first_set else '') + "', \\\n"
            plot_gpi += "$data_rate_ratio" + str(x) + "    using ($1+" + str(x) + "+0.10):3              with points lc rgb '" + colors.GREEN + "' pointtype 7 pointsize 0.4 lw 1.5  title '" + ('Rate ratio' if is_first_set else '') + "', \\\n"

            # gray lines between average values
            plot_gpi += "$data_window_ratio" + str(x) + "  using ($1+" + str(x) + "+0.00):3     with lines lc rgb 'gray'         title '', \\\n"
            plot_gpi += "$data_rate_ratio" + str(x) + "    using ($1+" + str(x) + "+0.10):3     with lines lc rgb 'gray'         title '', \\\n"

        treeutil.walk_leaf(tree, leaf)
        gpi += """
            plot \\
            """ + add_plot(plot_gpi) + """

            unset arrow 100
            unset logscale y
            """

        return {
            'y_logarithmic': y_logarithmic,
            'gpi': gpi,
        }

    return plot
