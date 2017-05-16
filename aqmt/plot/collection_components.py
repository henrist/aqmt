import math

from .common import add_plot, add_scale
from . import collectionutil
from . import treeutil
from . import colors


def utilization_total_only(y_logarithmic=False):
    """
    Plot graph of total utilization only
    """

    def plot(tree, plotdef, leaf_hook):
        gap = collectionutil.get_gap(tree)

        gpi = """
            # utilization
            set style line 100 lt 1 lc rgb 'black' lw 1.5 dt 3
            set arrow 100 from graph 0, first 100 to graph 1, first 100 nohead ls 100 back

            set ylabel "Utilization [%]\\n{/Times:Italic=10 (p_1, mean, p_{99})}"
            """ + add_scale(y_logarithmic, range_from_log='0.1', range_to='*<105', range_to_log='105')

        # add hidden line to force autoscaling if using logarithimic plot without any points
        plot_gpi = " 1 lc rgb '#FFFF0000' notitle, \\\n"

        def leaf(subtree, is_first_set, x):
            nonlocal plot_gpi, gpi
            leaf_hook(subtree, is_first_set, x)

            gpi += """
                $data_util""" + str(x) + """ << EOD
                """ + collectionutil.merge_testcase_data(subtree, 'aggregated/util_stats', plotdef.x_axis) + """
                EOD
                """

            xpos = "($1+" + str(x) + ")"
            xtic = "" if plotdef.custom_xtics else ":xtic(2)"

            plot_gpi += "$data_util" + str(x) + "      using " + xpos + ":3:10:6  with yerrorbars ls 1 pointtype 7 pointsize 0.4 lc rgb '" + colors.AGGR + "' lw 1.5 notitle, \\\n"
            plot_gpi += "''                            using " + xpos + ":3" + xtic + "   with lines      lc rgb 'gray'         title '', \\\n"

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
            'key_rows': 0,
        }

    return plot


def utilization_queues(y_logarithmic=False, keys=True):
    """
    Plot graph of utilization for total, ECN and non-ECN flows
    """

    def plot(tree, plotdef, leaf_hook):
        gap = collectionutil.get_gap(tree)

        gpi = """
            # utilization
            set style line 100 lt 1 lc rgb 'black' lw 1.5 dt 3
            set arrow 100 from graph 0, first 100 to graph 1, first 100 nohead ls 100 back

            set ylabel "Utilization [%]\\n{/Times:Italic=10 (p_1, mean, p_{99})}"
            """ + add_scale(y_logarithmic, range_from_log='0.1', range_to='*<105', range_to_log='105')

        # add hidden line to force autoscaling if using logarithimic plot without any points
        plot_gpi = " 1 lc rgb '#FFFF0000' notitle, \\\n"

        def leaf(subtree, is_first_set, x):
            nonlocal plot_gpi, gpi
            leaf_hook(subtree, is_first_set, x)
            add_title = keys and is_first_set

            gpi += """
                $data_util""" + str(x) + """ << EOD
                """ + collectionutil.merge_testcase_data(subtree, 'aggregated/util_stats', plotdef.x_axis) + """
                EOD
                $data_util_ecn""" + str(x) + """ << EOD
                """ + collectionutil.merge_testcase_data(subtree, 'aggregated/util_ecn_stats', plotdef.x_axis) + """
                EOD
                $data_util_nonecn""" + str(x) + """ << EOD
                """ + collectionutil.merge_testcase_data(subtree, 'aggregated/util_nonecn_stats', plotdef.x_axis) + """
                EOD"""

            x0 = "($1+" + str(x) + "-" + str(gap/2) + ")"
            x1 = "($1+" + str(x) + ")"
            x2 = "($1+" + str(x) + "+" + str(gap/2) + ")"

            xtic = "" if plotdef.custom_xtics else ":xtic(2)"

            # total
            plot_gpi += "$data_util" + str(x) + "      using " + x0 + ":3:10:6     with yerrorbars ls 1 pointtype 7 pointsize 0.4 lc rgb '" + colors.AGGR + "' lw 1.5 title '" + ('All flows' if add_title else '') + "', \\\n"
           #plot_gpi += "''                            using " + x0 + ":7          with points     ls 1 pointtype 1 pointsize 0.4        title '', \\\n"
           #plot_gpi += "''                            using " + x0 + ":9          with points     ls 1 pointtype 1 pointsize 0.4        title '', \\\n"
            plot_gpi += "''                            using " + x0 + ":3          with lines      lc rgb 'gray'         title '', \\\n"

            # ecn
            plot_gpi += "$data_util_ecn" + str(x) + "  using " + x1 + ":3:10:6" + xtic + "  with yerrorbars ls 2 pointtype 2 pointsize 0.6 lc rgb '" + colors.L4S + "' lw 1.5 title '" + ('ECN' if add_title else '') + "', \\\n"
           #plot_gpi += "''                            using " + x1 + ":7                    with points     ls 2 pointtype 1 pointsize 0.4        title '', \\\n"
           #plot_gpi += "''                            using " + x1 + ":9                    with points     ls 2 pointtype 1 pointsize 0.4        title '', \\\n"
            plot_gpi += "''                            using " + x1 + ":3                    with lines      lc rgb 'gray'         title '', \\\n"

            # nonecn
            plot_gpi += "$data_util_nonecn" + str(x) + "  using " + x2 + ":3:10:6  with yerrorbars ls 3 pointtype 1 pointsize 0.6 lc rgb '" + colors.CLASSIC + "' lw 1.5 title '" + ('Non-ECN' if add_title else '') + "', \\\n"
           #plot_gpi += "''                               using " + x2 + ":7       with points     ls 3 pointtype 1 pointsize 0.4        title '', \\\n"
           #plot_gpi += "''                               using " + x2 + ":9       with points     ls 3 pointtype 1 pointsize 0.4        title '', \\\n"
            plot_gpi += "''                               using " + x2 + ":3       with lines      lc rgb 'gray'         title '', \\\n"

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
            'key_rows': 1 if keys else 0,
        }

    return plot


def utilization_tags(y_logarithmic=False, keys=True,
        range_from=None, range_from_log=None,
        range_to=None, range_to_log=None):
    """
    Plot graph of utilization for classified (tagged) traffic
    """
    pt_generator = collectionutil.pt_generator()

    if range_from_log is None:
        range_from_log = '0.1'
    if range_to is None:
        range_to = '*<105'
    if range_to_log is None:
        range_to_log = '105'

    def plot(tree, plotdef, leaf_hook):
        gap = collectionutil.get_gap(tree)

        gpi = """
            # utilization of tags
            set style line 100 lt 1 lc rgb 'black' lw 1.5 dt 3
            set arrow 100 from graph 0, first 100 to graph 1, first 100 nohead ls 100 back

            set ylabel "Utilization [%]\\n{/Times:Italic=10 (p_{25}, mean, p_{75})}"
            """ + add_scale(
                y_logarithmic,
                range_from=range_from, range_from_log=range_from_log,
                range_to=range_to, range_to_log=range_to_log
            )

        # add hidden line to force autoscaling if using logarithimic plot without any points
        plot_gpi = " 1 lc rgb '#FFFF0000' notitle, \\\n"

        plot_lines = ''
        titles_used = []

        def leaf(subtree, is_first_set, x):
            nonlocal plot_gpi, plot_lines, gpi, titles_used
            leaf_hook(subtree, is_first_set, x)
            add_title = keys and is_first_set

            gpi += """
                $dataUtil""" + str(x) + """ << EOD
                """ + collectionutil.merge_testcase_data(subtree, 'aggregated/util_stats', plotdef.x_axis) + """
                EOD"""

            # total
            xpos = "($1+" + str(x) + ")"
            xtic = "" if plotdef.custom_xtics else ":xtic(2)"
            plot_gpi   += "$dataUtil" + str(x) + "  using " + xpos + ":3:9:7" + xtic + "    with yerrorbars ls 1 pointtype 7 pointsize 0.4 lc rgb '" + colors.AGGR + "' lw 1.5 title '" + ('All flows' if add_title else '') + "', \\\n"
            plot_lines += "$dataUtil" + str(x) + "  using " + xpos + ":3                     with lines lc rgb 'gray'         title '', \\\n"

            tagged_flows = collectionutil.merge_testcase_data_group(subtree, 'aggregated/util_tagged_stats', plotdef.x_axis)
            x_distance = gap / (len(tagged_flows) + 1)

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

                pt = str(pt_generator(tagname))
                xpos = "($1+" + str(x + ((i + 1) * x_distance)) + ")"
                plot_gpi   += "$dataUtil" + str(x) + "_" + str(i) + "  using " + xpos + ":($4*100):($10*99):($8*100)  with yerrorbars ls 1 pointtype " + pt + " pointsize 0.6 lc rgb '" + colors.get_from_tagname(tagname) + "' lw 1.5 title '" + title + "', \\\n"
                plot_lines += "$dataUtil" + str(x) + "_" + str(i) + "  using " + xpos + ":($4*100)                    with lines lc rgb 'gray' title '', \\\n"

        treeutil.walk_leaf(tree, leaf)

        gpi += """
            plot \\
            """ + add_plot(plot_gpi + plot_lines) + """

            unset arrow 100
            unset logscale y
            """

        col_size = round(4 * pow(plotdef.x_scale, 1.2))
        return {
            'y_logarithmic': y_logarithmic,
            'gpi': gpi,
            'key_rows': math.ceil((len(titles_used) + 1) / col_size),
        }

    return plot


def queueing_delay(y_logarithmic=False, keys=True,
        range_from=None, range_from_log=None,
        range_to=None, range_to_log=None):
    """
    Plot graph of queueing delay
    """

    if range_from_log is None:
        range_from_log = '0.1'
    if range_to is None:
        range_to = '5<*'

    def plot(tree, plotdef, leaf_hook):
        gap = collectionutil.get_gap(tree)

        gpi = """
            # queueing delay
            set ylabel "Queueing delay [ms]\\n{/Times:Italic=10 (p_1, p_{25}, mean, p_{75}, p_{99})}"
            #set xtic offset first .1
            """ + add_scale(
                y_logarithmic,
                range_from=range_from, range_from_log=range_from_log,
                range_to=range_to, range_to_log=range_to_log
            )

        # add hidden line to force autoscaling if using logarithimic plot without any points
        plot_gpi = " 1 lc rgb '#FFFF0000' notitle, \\\n"

        def leaf(subtree, is_first_set, x):
            nonlocal gpi, plot_gpi
            leaf_hook(subtree, is_first_set, x)
            add_title = keys and is_first_set

            gpi += """
                $data_queue_ecn_stats""" + str(x) + """ << EOD
                """ + collectionutil.merge_testcase_data(subtree, 'aggregated/queue_ecn_stats', plotdef.x_axis) + """
                EOD
                $data_queue_nonecn_stats""" + str(x) + """ << EOD
                """ + collectionutil.merge_testcase_data(subtree, 'aggregated/queue_nonecn_stats', plotdef.x_axis) + """
                EOD"""

            ls_l4s = "ls 1 lc rgb '" + colors.L4S + "'"
            ls_classic = "ls 1 lc rgb '" + colors.CLASSIC + "'"

            x0 = "($1+" + str(x) + ")"
            x1 = "($1+" + str(x) + "+" + str(gap/2) + ")"
            xtic = "" if plotdef.custom_xtics else ":xtic(2)"

            plot_gpi += "$data_queue_ecn_stats" + str(x) + "    using " + x0 + ":($3/1000):($7/1000):($9/1000)              with yerrorbars " + ls_l4s + "     lw 1.5 pointtype 1 pointsize 0.6 title '" + ('ECN packets' if add_title else '') + "', \\\n"
            plot_gpi += "''                                     using " + x0 + ":($6/1000)                                  with points     " + ls_l4s + "            pointtype 1 pointsize 0.4 title '', \\\n"
            plot_gpi += "''                                     using " + x0 + ":($10/1000)                                 with points     " + ls_l4s + "            pointtype 1 pointsize 0.4 title '', \\\n"
            plot_gpi += "$data_queue_nonecn_stats" + str(x) + " using " + x1 + ":($3/1000):($7/1000):($9/1000)" + xtic + " with yerrorbars " + ls_classic + " lw 1.5 pointtype 8 pointsize 0.6 title '" + ('Non-ECN packets' if add_title else '') + "', \\\n"
            plot_gpi += "''                                     using " + x1 + ":($6/1000)                                  with points     " + ls_classic + "        pointtype 1 pointsize 0.4 title '', \\\n"
            plot_gpi += "''                                     using " + x1 + ":($10/1000)                                 with points     " + ls_classic + "        pointtype 1 pointsize 0.4 title '', \\\n"

            plot_gpi += "$data_queue_ecn_stats" + str(x) + "    using " + x0 + ":($3/1000)                                  with lines lc rgb 'gray'         title '', \\\n"
            plot_gpi += "$data_queue_nonecn_stats" + str(x) + " using " + x1 + ":($3/1000)                                  with lines lc rgb 'gray'         title '', \\\n"

        treeutil.walk_leaf(tree, leaf)
        gpi += """
            plot \\
            """ + add_plot(plot_gpi) + """

            unset logscale y
            """

        return {
            'y_logarithmic': y_logarithmic,
            'gpi': gpi,
            'key_rows': 1 if keys else 0,
        }

    return plot


def window(y_logarithmic=False, keys=True):
    """
    Plot graph of estimated congestion window

    Note that this currently is the sum for all flows
    """

    def plot(tree, plotdef, leaf_hook):
        gap = collectionutil.get_gap(tree)

        gpi = """
            set ylabel "Window size\\n{/Times:Italic=10 (Estimated) [1448 B]}\\n{/Times:Italic=10 (p_1, p_{25}, mean, p_{75}, p_{99})}"
            """ + add_scale(y_logarithmic)

        # add hidden line to force autoscaling if using logarithimic plot without any points
        plot_gpi = " 1 lc rgb '#FFFF0000' notitle, \\\n"

        def leaf(subtree, is_first_set, x):
            nonlocal gpi, plot_gpi
            leaf_hook(subtree, is_first_set, x)
            add_title = keys and is_first_set

            gpi += """
                $data_window_ecn_stats""" + str(x) + """ << EOD
                """ + collectionutil.merge_testcase_data(subtree, 'aggregated/window_ecn_stats', plotdef.x_axis) + """
                EOD
                $data_window_nonecn_stats""" + str(x) + """ << EOD
                """ + collectionutil.merge_testcase_data(subtree, 'aggregated/window_nonecn_stats', plotdef.x_axis) + """
                EOD"""

            ls_l4s = "ls 1 lc rgb '" + colors.L4S + "'"
            ls_classic = "ls 1 lc rgb '" + colors.CLASSIC + "'"

            x0 = "($1+" + str(x) + ")"
            x1 = "($1+" + str(x) + "+" + str(gap/2) + ")"
            xtic = "" if plotdef.custom_xtics else ":xtic(2)"

            plot_gpi += "$data_window_ecn_stats" + str(x) + "    using " + x0 + ":($3/1448/8):($7/1448/8):($9/1448/8)              with yerrorbars " + ls_l4s + "     lw 1.5 pointtype 7 pointsize 0.4 title '" + ('ECN packets' if add_title else '') + "', \\\n"
            plot_gpi += "''                                     using " + x0 + ":($6/1448/8)                                  with points     " + ls_l4s + "            pointtype 1 pointsize 0.4 title '', \\\n"
            plot_gpi += "''                                     using " + x0 + ":($10/1448/8)                                 with points     " + ls_l4s + "            pointtype 1 pointsize 0.4 title '', \\\n"
            plot_gpi += "$data_window_nonecn_stats" + str(x) + " using " + x1 + ":($3/1448/8):($7/1448/8):($9/1448/8)" + xtic + " with yerrorbars " + ls_classic + " lw 1.5 pointtype 7 pointsize 0.4 title '" + ('Non-ECN packets' if add_title else '') + "', \\\n"
            plot_gpi += "''                                     using " + x1 + ":($6/1448/8)                                  with points     " + ls_classic + "        pointtype 1 pointsize 0.4 title '', \\\n"
            plot_gpi += "''                                     using " + x1 + ":($10/1448/8)                                 with points     " + ls_classic + "        pointtype 1 pointsize 0.4 title '', \\\n"

            plot_gpi += "$data_window_ecn_stats" + str(x) + "    using " + x0 + ":($3/1448/8)                                  with lines lc rgb 'gray'         title '', \\\n"
            plot_gpi += "$data_window_nonecn_stats" + str(x) + " using " + x1 + ":($3/1448/8)                                  with lines lc rgb 'gray'         title '', \\\n"

        treeutil.walk_leaf(tree, leaf)
        gpi += """
            plot \\
            """ + add_plot(plot_gpi) + """

            unset logscale y
            """

        return {
            'y_logarithmic': y_logarithmic,
            'gpi': gpi,
            'key_rows': 1 if keys else 0,
        }

    return plot


def drops_marks(y_logarithmic=False, keys=True):
    """
    Plot graph of drop and marks for ECN and non-ECN queues
    """

    def plot(tree, plotdef, leaf_hook):
        gap = collectionutil.get_gap(tree)

        gpi = """
            # drops and marks
            set ylabel "Drop/marks [%]\\n{/Times=10 (of total traffic in the queue)}\\n{/Times:Italic=10 (p_1, p_{25}, mean, p_{75}, p_{99})}"
            set xtic offset first 0
            """ + add_scale(y_logarithmic, range_from_log='.1', range_to='1<*')

        # add hidden line to force autoscaling if using logarithimic plot without any points
        plot_gpi = " 1 lc rgb '#FFFF0000' notitle, \\\n"

        def leaf(subtree, is_first_set, x):
            nonlocal gpi, plot_gpi
            leaf_hook(subtree, is_first_set, x)
            add_title = keys and is_first_set

            gpi += """
                $data_d_percent_ecn_stats""" + str(x) + """ << EOD
                """ + collectionutil.merge_testcase_data(subtree, 'aggregated/drops_percent_ecn_stats', plotdef.x_axis) + """
                EOD
                $data_m_percent_ecn_stats""" + str(x) + """ << EOD
                """ + collectionutil.merge_testcase_data(subtree, 'aggregated/marks_percent_ecn_stats', plotdef.x_axis) + """
                EOD
                $data_d_percent_nonecn_stats""" + str(x) + """ << EOD
                """ + collectionutil.merge_testcase_data(subtree, 'aggregated/drops_percent_nonecn_stats', plotdef.x_axis) + """
                EOD"""

            x0 = "($1+" + str(x) + "-" + str(gap/2) + ")"
            x1 = "($1+" + str(x) + ")"
            x2 = "($1+" + str(x) + "+" + str(gap/2) + ")"
            xtic = "" if plotdef.custom_xtics else ":xtic(2)"

            plot_gpi += "$data_d_percent_ecn_stats" + str(x) + "     using " + x0 + ":3:7:9              with yerrorbars lc rgb '" + colors.DROPS_L4S + "'     pointtype 1 pointsize 0.6 lw 1.5  title '" + ('Drops (ECN)' if add_title else '') + "', \\\n"
            plot_gpi += "''                                          using " + x0 + ":6                  with points     lc rgb '" + colors.DROPS_L4S + "'     pointtype 1 pointsize 0.4        title '', \\\n"
            plot_gpi += "''                                          using " + x0 + ":10                 with points     lc rgb '" + colors.DROPS_L4S + "'     pointtype 1 pointsize 0.4        title '', \\\n"
            plot_gpi += "$data_m_percent_ecn_stats" + str(x) + "     using " + x1 + ":3:7:9" + xtic + " with yerrorbars lc rgb '" + colors.MARKS_L4S + "'     pointtype 2 pointsize 0.6 lw 1.5  title '" + ('Marks (ECN)' if add_title else '') + "', \\\n"
            plot_gpi += "''                                          using " + x1 + ":6                  with points     lc rgb '" + colors.MARKS_L4S + "'     pointtype 1 pointsize 0.4        title '', \\\n"
            plot_gpi += "''                                          using " + x1 + ":10                 with points     lc rgb '" + colors.MARKS_L4S + "'     pointtype 1 pointsize 0.4        title '', \\\n"
            plot_gpi += "$data_d_percent_nonecn_stats" + str(x) + "  using " + x2 + ":3:7:9              with yerrorbars lc rgb '" + colors.DROPS_CLASSIC + "' pointtype 8 pointsize 0.6 lw 1.5  title '" + ('Drops (Non-ECN)' if add_title else '') + "', \\\n"
            plot_gpi += "''                                          using " + x2 + ":6                  with points     lc rgb '" + colors.DROPS_CLASSIC + "' pointtype 1 pointsize 0.4        title '', \\\n"
            plot_gpi += "''                                          using " + x2 + ":10                 with points     lc rgb '" + colors.DROPS_CLASSIC + "' pointtype 1 pointsize 0.4        title '', \\\n"

            # gray lines between average values
            plot_gpi += "$data_d_percent_ecn_stats" + str(x) + "     using " + x0 + ":3     with lines lc rgb 'gray'         title '', \\\n"
            plot_gpi += "$data_m_percent_ecn_stats" + str(x) + "     using " + x1 + ":3     with lines lc rgb 'gray'         title '', \\\n"
            plot_gpi += "$data_d_percent_nonecn_stats" + str(x) + "  using " + x2 + ":3     with lines lc rgb 'gray'         title '', \\\n"

        treeutil.walk_leaf(tree, leaf)
        gpi += """
            plot \\
            """ + add_plot(plot_gpi) + """

            unset logscale y
            """

        return {
            'y_logarithmic': y_logarithmic,
            'gpi': gpi,
            'key_rows': 1 if keys else 0,
        }

    return plot


def window_rate_ratio(y_logarithmic=False, keys=True):
    """
    Plot graph of window and rate ratio between ECN and non-ECN queues
    """

    def plot(tree, plotdef, leaf_hook):
        gap = collectionutil.get_gap(tree)

        gpi = """
            # window and rate ratio
            set ylabel "Window and rate ratio\\n{/Times:Italic=10 ECN over non-ECN}"
            set xtic offset first 0

            # line at y 1 (the perfect balance)
            set style line 100 lt 1 lc rgb 'black' lw 1.5 dt 3
            set arrow 100 from graph 0, first 1 to graph 1, first 1 nohead ls 100 back
            """ + add_scale(y_logarithmic, range_from='*<.5', range_from_log='.01', range_to='2<*')

        # add hidden line to force autoscaling if using logarithimic plot without any points
        plot_gpi = " 1 lc rgb '#FFFF0000' notitle, \\\n"

        def leaf(subtree, is_first_set, x):
            nonlocal gpi, plot_gpi
            leaf_hook(subtree, is_first_set, x)
            add_title = keys and is_first_set

            gpi += """
                $data_window_ratio""" + str(x) + """ << EOD
                """ + collectionutil.merge_testcase_data(subtree, 'aggregated/ecn_over_nonecn_window_ratio', plotdef.x_axis) + """
                EOD
                $data_rate_ratio""" + str(x) + """ << EOD
                """ + collectionutil.merge_testcase_data(subtree, 'aggregated/ecn_over_nonecn_rate_ratio', plotdef.x_axis) + """
                EOD
                """

            x0 = "($1+" + str(x) + ")"
            x1 = "($1+" + str(x) + "+" + str(gap/2) + ")"
            xtic = "" if plotdef.custom_xtics else ":xtic(2)"

            plot_gpi += "$data_window_ratio" + str(x) + "  using " + x0 + ":3" + xtic + " with points lc rgb '" + colors.BLACK + "' pointtype 7 pointsize 0.4 lw 1.5  title '" + ('Window ratio' if add_title else '') + "', \\\n"
            plot_gpi += "$data_rate_ratio" + str(x) + "    using " + x1 + ":3              with points lc rgb '" + colors.GREEN + "' pointtype 7 pointsize 0.4 lw 1.5  title '" + ('Rate ratio' if add_title else '') + "', \\\n"

            # gray lines between average values
            plot_gpi += "$data_window_ratio" + str(x) + "  using " + x0 + ":3     with lines lc rgb 'gray'         title '', \\\n"
            plot_gpi += "$data_rate_ratio" + str(x) + "    using " + x1 + ":3     with lines lc rgb 'gray'         title '', \\\n"

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
            'key_rows': 1 if keys else 0,
        }

    return plot
