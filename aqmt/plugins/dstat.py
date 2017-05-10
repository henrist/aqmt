"""
This plugin provides analysis of cpu statistics and
number of interrupts and context switches

Requirements:
- dstat (apt-get install dstat)
"""

from plumbum.cmd import dstat, bash
import os

from aqmt import processes
from aqmt.plot import collectionutil, treeutil
from aqmt.plot.common import add_plot, add_scale


def pre_hook(testcase):
    """
    Run dstat in the background of the test

    Field output in dstat.log:
      1     2   3   4   5   6   7    8   9     10    11    12   13
    epoch |usr sys idl wai hiq siq| int csw | read  writ| recv send>
                  cpu stats         system        io         net
    """
    dstatfile = testcase.test_folder + '/dstat.log'
    try:
        os.remove(dstatfile)
    except OSError:
        pass
    cmd = dstat['--output', dstatfile, '-Tcyrndgm']
    pid = testcase.testenv.run(cmd, bg=True)
    processes.add_known_pid(pid)


def plot_flow_cpu():
    def plot(testfolder, plotdef):
        label_y_pos = -0.06 * (1/plotdef.y_scale)
        gpi = """
            set format y "%g"
            set format x "%g s"
            set ylabel 'CPU usage'
            set yrange [0:100]
            set xrange [-2:*]

            set label "Time:" at graph -0.02, graph """ + str(label_y_pos) + """ font 'Times-Roman,11pt' tc rgb 'black' right

            # skip 7 first lines
            set datafile separator ","
            dstat = "\\"< awk '(NR>7){print;}' '""" + testfolder + """/dstat.log'\\""

            plot \\
                @dstat using ($0-2):($4+$2+$3+$6+$7+$5)  with filledcurve x1 lw 1.5 title 'idle', \\
                @dstat using ($0-2):($2+$3+$6+$7+$5)     with filledcurve x1 lw 1.5 title 'user', \\
                @dstat using ($0-2):($3+$6+$7+$5)        with filledcurve x1 lw 1.5 title 'system', \\
                @dstat using ($0-2):($6+$7+$5)           with filledcurve x1 lw 1.5 title 'hiq', \\
                @dstat using ($0-2):($7+$5)              with filledcurve x1 lw 1.5 title 'softirqs', \\
                @dstat using ($0-2):($5)                 with filledcurve x1 lw 1.5 title 'iowait'

            set format y "%h"
            unset datafile
            """
        return {
            'gpi': gpi,
            'skip_sample_line': True,
        }
    return plot



def plot_comparison_cpu(keys=True):
    """
    Plot graph of cpu usage
    """
    y_logarithmic = False

    def plot(tree, plotdef, leaf_hook):
        gap = collectionutil.get_gap(tree)

        gpi = """
            set ylabel "CPU usage [%]"
            """ + add_scale(y_logarithmic, range_to='100')

        # add hidden line to force autoscaling if using logarithimic plot without any points
        plot_gpi = " 1 lc rgb '#FFFF0000' notitle, \\\n"

        def leaf(subtree, is_first_set, x):
            nonlocal gpi, plot_gpi
            leaf_hook(subtree, is_first_set, x)
            add_title = keys and is_first_set

            def parse_cpu(testcase_folder):
                skip = 7
                fields = [
                    1,  # user
                    2,  # sys
                    3,  # idle
                    4,  # wai
                    5,  # hiq
                    6,  # siq
                ]
                items = [[] for item in fields]
                with open(testcase_folder + '/dstat.log') as f:
                    for line in f:
                        if skip > 0:
                            skip -= 1
                            continue

                        line = line.split(',')
                        for i, field in enumerate(fields):
                            items[i].append(float(line[field]))

                # for simplicity we take the second half of the list
                items = [x[int(len(x)/2):] for x in items]
                return ' '.join([str(sum(x)/len(x)) for x in items])

            gpi += """
                $data_cpu_idl""" + str(x) + """ << EOD
                """ + collectionutil.merge_testcase_data(subtree, parse_cpu, plotdef.x_axis) + """
                EOD
                """

            xpos = '($1+%s)' % str(x)
            xtic = "" if plotdef.custom_xtics else ":xtic(2)"
            plot_gpi += ("""\\
                %s   using """ + xpos + """:($5+$3+$4+$7+$8+$6) :(.8)%s  with boxes fc 1 lw 1.5 """ + ("title 'idle'    " if add_title else 'notitle') + """, \\
                ''   using """ + xpos + """:($3+$4+$7+$8+$6)    :(.8)    with boxes fc 2 lw 1.5 """ + ("title 'user'    " if add_title else 'notitle') + """, \\
                ''   using """ + xpos + """:($4+$7+$8+$7)       :(.8)    with boxes fc 3 lw 1.5 """ + ("title 'system'  " if add_title else 'notitle') + """, \\
                ''   using """ + xpos + """:($7+$8+$7)          :(.8)    with boxes fc 4 lw 1.5 """ + ("title 'hiq'     " if add_title else 'notitle') + """, \\
                ''   using """ + xpos + """:($8+$6)             :(.8)    with boxes fc 5 lw 1.5 """ + ("title 'softirqs'" if add_title else 'notitle') + """, \\
                ''   using """ + xpos + """:($6)                :(.8)    with boxes fc 6 lw 1.5 """ + ("title 'iowait'  " if add_title else 'notitle') + """, \\
                """) % ("$data_cpu_idl" + str(x), xtic)

        treeutil.walk_leaf(tree, leaf)
        gpi += """
            plot \\
            """ + add_plot(plot_gpi)

        return {
            'y_logarithmic': y_logarithmic,
            'gpi': gpi,
            'key_rows': 1 if keys else 0,
        }

    return plot



def plot_flow_int_csw():
    def plot(testfolder, plotdef):
        label_y_pos = -0.06 * (1/plotdef.y_scale)
        gpi = """
            set format y "%g"
            set format x "%g s"
            set ylabel 'System interrupts'
            set yrange [0:*]
            set xrange [-2:*]

            set label "Time:" at graph -0.01, graph """ + str(label_y_pos) + """ font 'Times-Roman,11pt' tc rgb 'black' right

            # skip 7 first lines
            set datafile separator ","
            dstat = "\\"< awk '(NR>7){print;}' '""" + testfolder + """/dstat.log'\\""

            plot \\
                @dstat using ($0-2):8 with lines lw 1.5 title 'interrupts', \\
                @dstat using ($0-2):9 with lines lw 1.5 title 'context switches'

            set format y "%h"
            unset datafile
            """
        return {
            'gpi': gpi,
            'skip_sample_line': True,
        }
    return plot


def plot_comparison_int_csw(y_logarithmic=False, keys=True):
    """
    Plot graph of interrupts and context switches
    """

    def plot(tree, plotdef, leaf_hook):
        gap = collectionutil.get_gap(tree)

        gpi = """
            set ylabel "System stats\\n{/Times:Italic=10 Average values}"
            """ + add_scale(y_logarithmic)

        # add hidden line to force autoscaling if using logarithimic plot without any points
        plot_gpi = " 1 lc rgb '#FFFF0000' notitle, \\\n"

        def leaf(subtree, is_first_set, x):
            nonlocal gpi, plot_gpi
            leaf_hook(subtree, is_first_set, x)
            add_title = keys and is_first_set

            def parse_int_csw(testcase_folder):
                skip = 7
                fields = [
                    7,  # interrupts
                    8,  # context switches
                ]
                items = [[] for item in fields]
                with open(testcase_folder + '/dstat.log') as f:
                    for line in f:
                        if skip > 0:
                            skip -= 1
                            continue

                        line = line.split(',')
                        for i, field in enumerate(fields):
                            items[i].append(float(line[field]))

                # for simplicity we take the second half of the list
                items = [x[int(len(x)/2):] for x in items]
                return ' '.join([str(sum(x)/len(x)) for x in items])

            gpi += """
                $data_int_csw""" + str(x) + """ << EOD
                """ + collectionutil.merge_testcase_data(subtree, parse_int_csw, plotdef.x_axis) + """
                EOD
                """

            xpos = '($1+%s)' % str(x)
            xtic = "" if plotdef.custom_xtics else ":xtic(2)"
            plot_gpi += ("""\\
                %s   using """ + xpos + """:3%s  with linespoints lc 1 pt 7 ps 0.4 lw 1.5 """ + ("title 'interrupts'       " if add_title else 'notitle') + """, \\
                ''   using """ + xpos + """:4    with linespoints lc 2 pt 7 ps 0.4 lw 1.5 """ + ("title 'context switches' " if add_title else 'notitle') + """, \\
                """) % ("$data_int_csw" + str(x), xtic)

        treeutil.walk_leaf(tree, leaf)
        gpi += """
            plot \\
            """ + add_plot(plot_gpi)

        return {
            'y_logarithmic': y_logarithmic,
            'gpi': gpi,
            'key_rows': 1 if keys else 0,
        }

    return plot
