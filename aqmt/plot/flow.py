from .common import plot_header


def get_aggregated_samples_to_skip(testfolder):
    with open(testfolder + '/details', 'r') as f:
        for line in f:
            if line.startswith('analyzed_aggregated_samples_skipped'):
                return int(line.split()[1])

    return 0


def get_number_samples(testfolder):
    """
    Get the number of samples this test consists of.

    We avoid looking at ta_samples in details-file because
    the test might have been interrupted.
    """
    n = 0
    with open(testfolder + '/ta/rate', 'r') as f:
        for _ in f:
            n += 1

    return n


def build_plot(testfolder, components, x_scale=1, y_scale=1):
    """
    Generate a plot for a single test case
    """

    aggregated_samples_to_skip = get_aggregated_samples_to_skip(testfolder)

    gpi = plot_header()
    gpi += """
        set multiplot layout """ + str(len(components)) + """,1 columnsfirst title '""" + testfolder + """'
        set offset graph 0.02, graph 0.02, graph 0.02, graph 0.02
        set lmargin 13
        set xrange [1:""" + str(get_number_samples(testfolder)) + """]

        # draw line where the statistics for aggregated data is collected from
        set style line 100 lt 1 lc rgb 'red' lw .5 dt 7
        set arrow from first """ + str(aggregated_samples_to_skip - .5) + """, graph 0 to first """ + str(aggregated_samples_to_skip - .5) + """, graph 1 nohead ls 100 back
        """

    i = 0
    for component in components:
        # show xlabel at bottom of the multiplot, so do it only for latest component
        if i + 1 == len(components):
            gpi += """
                set xlabel 'Sample #'
                """

        gpi += component(testfolder)
        i += 1

    gpi += """
        unset multiplot
        reset"""

    return {
        'gpi': gpi,
        'width': '%fcm' % (x_scale * 21),
        'height': '%fcm' % (y_scale * 7.5 * len(components)),
    }


def build_multiple_plot(testfolders, components, **kwargs):
    """
    Generate a PDF with one page with graphs per flow
    """

    gpi = ""
    width = None
    height = None

    for testfolder in testfolders:
        res = build_plot(testfolder, components, **kwargs)
        gpi += res['gpi']
        width = res['width']
        height = res['height']

    return {
        'gpi': gpi,
        'width': width,
        'height': height,
    }
