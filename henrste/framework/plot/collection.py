"""
Plot a collection of test cases

It is assumed that all leafs are of the same structure,
but not necessary same amount of test cases inside
a leaf
"""

from .common import PlotAxis, plot_header
from . import collectionutil
from . import treeutil


def is_custom_xtics(x_axis):
    return x_axis != PlotAxis.CATEGORY and False


def get_tmargin_base(tree):
    _, _, n_depth, _ = collectionutil.get_tree_details(tree)
    tmargin_base = 1 * n_depth + 2
    if 'subtitle' in tree and tree['subtitle']:
        tmargin_base += .8
    return tmargin_base


def line_at_x_offset(xoffset, value_at_x, testmeta, x_axis):
    xpos = get_x_coordinate(testmeta, value_at_x, x_axis)

    return """
        set style line 100 lt 1 lc rgb 'red' lw .5 dt 7
        set arrow from first """ + str(xpos+xoffset) + """, graph 0 to first """ + str(xpos+xoffset) + """, graph 1 nohead ls 100 back
    """


def plot_labels(tree):
    """
    Plot labels located above the graphs
    """

    gpi = ""
    depth_sizes = treeutil.get_depth_sizes(tree)
    _, _, n_depth, _ = collectionutil.get_tree_details(tree)

    def branch(treenode, x, depth, width):
        nonlocal gpi
        fontsize = fontsize = max(5, min(9, 10 - depth_sizes[depth] / 4.5))

        centering = False
        x_offset = x + (width - 2) / 2 if centering else x

        gpi += """
            set label \"""" + treenode['title'] + """\" at first """ + str(x_offset) + """, graph """ + str(1.05 + 0.06 * (n_depth - depth - 1)) + """ font 'Times-Roman,""" + str(fontsize) + """pt' tc rgb 'black' left"""

    treeutil.walk_tree_reverse(tree, branch)
    return gpi


def common_header(tree):
    _, _, _, n_nodes = collectionutil.get_tree_details(tree)

    gpi = """
        unset bars
        set xtic rotate by -65 font ',""" + str(max(3, min(10, 15 - n_nodes / 18))) + """'
        set key above
        set xrange [-2:""" + str(n_nodes + 1) + """]
        set boxwidth 0.2
        set tmargin """ + str(get_tmargin_base(tree)) + """
        set lmargin 13
        """

    return gpi


def plot_title(tree, n_components):
    title = tree['title']
    if 'subtitle' in tree and tree['subtitle']:
        title += '\\n' + tree['subtitle']

    return """
        set multiplot layout """ + str(n_components) + """,1 title \"""" + title + """\\n\" scale 1,1"""


def build_plot(tree, x_axis=PlotAxis.CATEGORY, components=None, lines_at_x_offset=None):
    """
    Plot the collection tree provided using the provided components
    """

    if lines_at_x_offset is None:
        lines_at_x_offset = []
    if components is None:
        components = []

    gpi = plot_header()
    gpi += plot_title(tree, len(components))
    gpi += plot_labels(tree)

    def leaf_hook(subtree, is_first_set, x):
        nonlocal gpi
        for xoffset in lines_at_x_offset:
            gpi += line_at_x_offset(x, xoffset, subtree, x_axis)

    i = 0
    for component in components:
        res = component(tree, x_axis, leaf_hook)
        gpi += common_header(tree)

        # show xlabel at bottom of the multiplot, so do it only for latest component
        if i + 1 == len(components):
            xlabel = collectionutil.get_xlabel(tree)
            if xlabel is not None:
                gpi += """
                    set xlabel '""" + xlabel + """'"""

        gpi += res['gpi']
        i += 1

    gpi += """
        unset multiplot"""

    return {
        'gpi': gpi,
        'width': '21cm',
        'height': '%dcm' % (7 * len(components)),
    }
