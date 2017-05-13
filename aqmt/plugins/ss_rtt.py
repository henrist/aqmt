"""
This plugin provides analysis of RTT reported by
the sender side. It basicly takes the average observed
rtt by `ss` command on the server.

If the traffic from a server goes to two different queues,
so the flows have different RTTs, the average value would
be wrong.
"""

import numpy as np
from functools import partial

from plumbum.cmd import bash
import operator
import os

from aqmt import processes
from aqmt.plot import collectionutil, treeutil
from aqmt.plot.common import add_plot, add_scale
from ..testenv import read_metadata


def pre_hook(testcase):
    """
    Run ss and collect server rtt stats in the background
    of the test. Calculates average rtt between all flows
    on each node.
    """
    for node in ['A', 'B']:
        cmd = bash['-c', """
            # We need to run the next command it in the background and wait
            # for it so that we can actually SIGTERM the bash process
            # causing the ssh connection to terminate and bash script
            # to end.
            ssh -tt """ + os.environ['IP_SERVER%s_MGMT' % node] + """ '
                getdata() {
                    ss -ni "( src %s or dst %s or src %s or dst %s )" | \\
                        grep -B1 " rtt:" | \\
                        awk "!(NR%%2){print $1\\" \\"p\\" XX \\"\\$0}{p=\\$5\\" \\"\\$6}" | \\
                        sed "s/XX.* rtt:\\([^\\/]\\+\\).*/\\1/"
                }
                start=$(($(date +%%s%%N)/1000000))
                while true; do
                    now=$(($(date +%%s%%N)/1000000))
                    getdata $((now-start))
                    sleep .1
                done
                ' >'%s' &
            sshpid=$!
            trap killssh TERM
            killssh() {
                kill $sshpid
                exit
            }
            wait
            """ % (
                os.environ['IP_CLIENTA'],
                os.environ['IP_CLIENTA'],
                os.environ['IP_CLIENTB'],
                os.environ['IP_CLIENTB'],
                testcase.test_folder + '/rtt-%s.log' % node
            )
        ]

        pid = testcase.testenv.run(cmd, bg=True)
        processes.add_known_pid(pid)


def _generate_stats(numbers):
    if len(numbers) == 0:
        res = ['-', '-', '-', '-', '-', '-', '-', '-', '-']
    else:
        res = [
            np.average(numbers).astype('str'),
            '-',  # not used: np.std(numbers).astype('str'),
            '-',  # not used: np.min(numbers).astype('str'),
            np.percentile(numbers, 1, interpolation='lower').astype('str'),
            '-',  # not used: np.percentile(numbers, 25, interpolation='lower').astype('str'),
            '-',  # not used: np.percentile(numbers, 50, interpolation='lower').astype('str'),
            '-',  # not used: np.percentile(numbers, 75, interpolation='lower').astype('str'),
            np.percentile(numbers, 99, interpolation='lower').astype('str'),
            '-',  # not used: np.max(numbers).astype('str'),
        ]

    return ' '.join(res)


def _parse_rtt_of_test(testfolder, node, subtract_base_rtt):
    # make tables with sums
    table_n = {}
    table_rtt = {}

    subtract = 0
    if subtract_base_rtt:
        metadata_kv, metadata_lines = read_metadata(testfolder + '/details')
        subtract = float(metadata_kv['testbed_rtt_clients'])
        subtract += float(metadata_kv['testbed_rtt_server%s' % node.lower()])

    with open(testfolder + '/rtt-%s.log' %  node) as f:
        for line in f:
            i, src, dst, rtt = line.split()
            i = int(i)

            if i not in table_n:
                table_n[i] = 0
                table_rtt[i] = 0

            table_n[i] += 1
            table_rtt[i] += float(rtt) - subtract

    # make average within each sample
    ret = []
    for i, n in sorted(table_n.items(), key=operator.itemgetter(0)):
        ret.append((i, table_rtt[i] / n))
    return ret


def plot_flow_rtt(initial_delay=0, subtract_base_rtt=False):
    """
    Initial delay is number of seconds the recording started
    before the actual test started.
    """

    def get_list(testfolder, node):
        ret = ''
        for i, rtt in _parse_rtt_of_test(testfolder, node, subtract_base_rtt):
            ret += '%s %f\n' % (i, rtt)
        return ret


    def plot(testfolder, plotdef):
        label_y_pos = -0.06 * (1/plotdef.y_scale)
        xpos = "($1/1000-" + str(initial_delay) + ")"

        ylabel_extra = ''
        if subtract_base_rtt:
            ylabel_extra = '\\n{/Times:Italic=10 Excluding base RTT}'

        data_a = get_list(testfolder, 'A')
        data_b = get_list(testfolder, 'B')

        x_max = max(
            [0] +
            [int(x.split()[0]) for x in data_a.splitlines()] +
            [int(x.split()[0]) for x in data_b.splitlines()]
        ) / 1000

        gpi = """
            set format y "%g"
            set format x "%g s"
            set ylabel "RTT reported at sender [ms]""" + ylabel_extra + """"
            set yrange [0<*:*]

            set label "Time:" at graph -0.01, graph """ + str(label_y_pos) + """ font 'Times-Roman,11pt' tc rgb 'black' right

            $data_node_a << EOD
            """ + data_a + """
            EOD
            $data_node_b << EOD
            """ + data_b + """
            EOD

            set xrange [-""" + str(initial_delay) + """:""" + str(x_max - initial_delay) + """]

            plot \\
                1 lc rgb '#FFFF0000' notitle, \\
                $data_node_a using """ + xpos + """:2               with lines   lc 1 lw 1.5 title 'Avg. RTT node A', \\
                $data_node_a using """ + xpos + """:2 smooth bezier with lines   lc 1 lw 3 notitle, \\
                $data_node_b using """ + xpos + """:2               with lines   lc 2 lw 1.5 title 'Avg. RTT node B', \\
                $data_node_b using """ + xpos + """:2 smooth bezier with lines   lc 2 lw 3 notitle

            set format y "%h"
            """
        return {
            'gpi': gpi,
            'skip_sample_line': True,
        }
    return plot


def plot_comparison_rtt(y_logarithmic=False, keys=True, subtract_base_rtt=False):
    """
    Plot graph of interrupts and context switches
    """

    def plot(tree, plotdef, leaf_hook):
        gap = collectionutil.get_gap(tree)

        ylabel_extra = ''
        if subtract_base_rtt:
            ylabel_extra = '\\n{/Times:Italic=10 Excluding base RTT}'

        gpi = """
            set ylabel "RTT reported at sender""" + ylabel_extra + """\\n{/Times:Italic=10 [ms] (p_1, mean, p_{99})}"
            """ + add_scale(y_logarithmic)

        # add hidden line to force autoscaling if using logarithimic plot without any points
        plot_gpi = " 1 lc rgb '#FFFF0000' notitle, \\\n"

        def leaf(subtree, is_first_set, x):
            nonlocal gpi, plot_gpi
            leaf_hook(subtree, is_first_set, x)
            add_title = keys and is_first_set

            def parse_rtt(node, testcase_folder):
                rtts = _parse_rtt_of_test(testcase_folder, node, subtract_base_rtt)

                # take last half, so it is stable
                rtts = rtts[int(len(rtts)/2):]

                # get second element of list which is the rtt value
                rtts = [x[1] for x in rtts]

                return _generate_stats(rtts)

            gpi += """
                $data_rtt_a""" + str(x) + """ << EOD
                """ + collectionutil.merge_testcase_data(subtree, partial(parse_rtt, 'A'), plotdef.x_axis) + """
                EOD
                $data_rtt_b""" + str(x) + """ << EOD
                """ + collectionutil.merge_testcase_data(subtree, partial(parse_rtt, 'B'), plotdef.x_axis) + """
                EOD
                """

            xpos = '($1+%s)' % str(x)
            xtic = "" if plotdef.custom_xtics else ":xtic(2)"

            plot_gpi += ("""\\
                %s   using """ + xpos + """:3:10:6%s  with yerrorbars ls 3 pt 7 ps 0.4 lw 1.5 lc 1 %s, \\
                ''   using """ + xpos + """:3         with lines      lc rgb 'gray' notitle, \\
                %s   using """ + xpos + """:3:10:6%s  with yerrorbars ls 3 pt 7 ps 0.4 lw 1.5 lc 2 %s, \\
                ''   using """ + xpos + """:3         with lines      lc rgb 'gray' notitle, \\
                """) % (
                    "$data_rtt_a" + str(x),
                    xtic,
                    "title 'Server A' " if add_title else 'notitle',
                    "$data_rtt_b" + str(x),
                    xtic,
                    "title 'Server B' " if add_title else 'notitle'
                )

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
