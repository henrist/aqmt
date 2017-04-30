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


def build_plot(testfolder, components, x_scale=1, y_scale=1, title='DEFAULT',
        skip_sample_line=False):
    """
    Generate a plot for a single test case
    """

    aggregated_samples_to_skip = get_aggregated_samples_to_skip(testfolder)
    n_samples = get_number_samples(testfolder)

    def plot_container(result):
        plot_title = ''
        if title == 'DEFAULT':
            plot_title = "title '" + testfolder + "'"
        elif title is not None:
            plot_title = "title '" + title + "'"

        result['gpi'] = plot_header() + """
            set multiplot layout """ + str(len(components)) + """,1 columnsfirst """ + plot_title + """
            set offset graph 0.02, graph 0.02, graph 0.02, graph 0.02
            set lmargin 14
            set xtic font ',11'

            """ + result['gpi'] + """
            unset multiplot
            reset
            """
        result['width'] = '%fcm' % (x_scale * 21)
        result['height'] = '%fcm' % (y_scale * 7.5 * len(components))
        return result

    def add_sample_line(result):
        result['gpi'] = """
            # draw line where the statistics for aggregated data is collected from
            set style line 100 lt 1 lc rgb 'red' lw .5 dt 7
            set arrow 111 \\
                from first """ + str(aggregated_samples_to_skip - .5) + """, graph 0 \\
                to first """ + str(aggregated_samples_to_skip - .5) + """, graph 1 \\
                nohead ls 100 back

            """ + result['gpi'] + """

            unset arrow 111
            """
        return result

    def component_container(result):
        if not skip_sample_line and \
                ('skip_sample_line' not in result or \
                    not result['skip_sample_line']):
            result = add_sample_line(result)
        return result

    def merge_components():
        result = {'gpi': ''}

        for component in components:
            comp_result = component_container(
                component(testfolder)
            )
            result['gpi'] += """
                set xrange [1:""" + str(n_samples) + """]
                """ + comp_result['gpi']

        return result

    return plot_container(merge_components())


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
