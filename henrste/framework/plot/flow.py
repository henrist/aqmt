from .common import plot_header


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


def build_plot(testfolder, components):
    """
    Generate a plot for a single test case
    """

    gpi = plot_header()
    gpi += """
        set multiplot layout """ + str(len(components)) + """,1 columnsfirst title '""" + testfolder + """'
        set offset graph 0.02, graph 0.02, graph 0.02, graph 0.02
        set lmargin 13
        set xrange [1:""" + str(get_number_samples(testfolder)) + """]
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
        'width': '21cm',
        'height': '%fcm' % (len(components) * 7.5),
    }


def build_multiple_plot(testfolders, components):
    """
    Generate a PDF with one page with graphs per flow
    """

    gpi = ""
    width = None
    height = None

    for testfolder in testfolders:
        res = build_plot(testfolder, components)
        gpi += res['gpi']
        width = res['width']
        height = res['height']

    return {
        'gpi': gpi,
        'width': width,
        'height': height,
    }
