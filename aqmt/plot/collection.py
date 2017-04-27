"""
Plot a collection of test cases

It is assumed that all leafs are of the same structure,
but not necessary same amount of test cases inside
a leaf
"""

from .common import PlotAxis, plot_header
from . import collectionutil
from . import treeutil


def get_tmargin_base(tree):
    _, _, n_depth, _ = collectionutil.get_tree_details(tree)
    return .65 * n_depth + 2.8


def line_at_x_offset(xoffset, value_at_x, testmeta, x_axis):
    xpos = collectionutil.get_x_coordinate(testmeta, value_at_x, x_axis)

    return """
        set style line 100 lt 1 lc rgb 'red' lw .5 dt 7
        set arrow from first """ + str(xpos+xoffset) + """, graph 0 to first """ + str(xpos+xoffset) + """, graph 1 nohead ls 100 back
    """


def plot_labels(tree, plot_width):
    """
    Plot labels located above the graphs
    """

    # calculate the position where the label is right aligned in the plot
    xpos = -0.005 * 28 / plot_width

    gpi = ""
    depth_sizes = treeutil.get_depth_sizes(tree)
    _, _, n_depth, _ = collectionutil.get_tree_details(tree)
    first_titlelabel = {}

    def branch(treenode, x, depth, width):
        nonlocal first_titlelabel, gpi
        fontsize = fontsize = max(6, min(10, 11 - depth_sizes[depth] / 10))

        centering = False
        x_offset = x + (width - 2) / 2 if centering else x

        if treenode['titlelabel'] != '' and depth not in first_titlelabel:
            first_titlelabel[depth] = False
            gpi += """
                set label \"""" + treenode['titlelabel'] + """:\" at graph """ + str(xpos) + """, graph """ + str(1.06 + 0.06 * (n_depth - depth - 1)) + """ font 'Times-Roman,""" + str(fontsize) + """pt' tc rgb 'black' right
                """

        gpi += """
            set label \"""" + treenode['title'] + """\" at first """ + str(x_offset) + """, graph """ + str(1.06 + 0.06 * (n_depth - depth - 1)) + """ font 'Times-Roman,""" + str(fontsize) + """pt' tc rgb 'black' left
            """

    treeutil.walk_tree_reverse(tree, branch)

    xlabel = collectionutil.get_xlabel(tree)
    if xlabel is not None:
        gpi += """
            set label \"""" + xlabel + """:\" at graph """ + str(xpos) + """, graph -.07 font 'Times-Roman,10pt' tc rgb 'black' right
            """

    return gpi


def common_header(tree):
    _, _, _, n_nodes = collectionutil.get_tree_details(tree)

    gpi = """
        unset bars
        set xtic rotate by -65 font ',""" + str(max(5, min(10, 15 - n_nodes / 18))) + """'
        set key above
        set xrange [-2:""" + str(n_nodes + 1) + """]
        set boxwidth 0.2
        set tmargin """ + str(get_tmargin_base(tree)) + """
        set lmargin 13
        """

    return gpi


def plot_title(tree, n_components):
    title = []
    if tree['title']:
        title.append(tree['title'])
    if 'subtitle' in tree and tree['subtitle']:
        title.append(tree['subtitle'])
    if len(title) > 0:
        title = 'title "%s\\n"' % ('\\n'.join(title))
    else: title = ''

    return """
        set multiplot layout """ + str(n_components) + """,1 %s scale 1,1""" % title


def build_plot(tree, x_axis=PlotAxis.CATEGORY, components=None, lines_at_x_offset=None, x_scale=1, y_scale=1):
    """
    Plot the collection tree provided using the provided components
    """

    if lines_at_x_offset is None:
        lines_at_x_offset = []
    if components is None:
        components = []

    width = x_scale * 21

    gpi = plot_header()
    gpi += plot_title(tree, len(components))
    gpi += plot_labels(tree, width)

    def leaf_hook(subtree, is_first_set, x):
        nonlocal gpi
        for xoffset in lines_at_x_offset:
            gpi += line_at_x_offset(x, xoffset, subtree, x_axis)

    for component in components:
        res = component(tree, x_axis, leaf_hook)
        gpi += common_header(tree)
        gpi += res['gpi']

    gpi += """
        unset multiplot"""

    return {
        'gpi': gpi,
        'width': '%fcm' % width,
        'height': '%fcm' % (y_scale * 7 * len(components)),
    }
