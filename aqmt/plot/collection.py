"""
Plot a collection of test cases

It is assumed that all leafs are of the same structure,
but not necessary same amount of test cases inside
a leaf
"""

from .common import PlotAxis, plot_header
from . import collectionutil
from . import treeutil

COMPONENT_HEIGHT = 7  # cm


def line_at_x_offset(xoffset, value_at_x, testmeta, x_axis):
    xpos = collectionutil.get_x_coordinate(testmeta, value_at_x, x_axis)

    return """
        set style line 100 lt 1 lc rgb 'red' lw .5 dt 7
        set arrow from first """ + str(xpos+xoffset) + """, graph 0 to first """ + str(xpos+xoffset) + """, graph 1 nohead ls 100 back
    """


def plot_labels(tree, plotdef, component, tmargin):
    """
    Plot labels located above the graphs
    """

    # attempt to calculate the height of the plot window and
    NORMAL_HEIGHT = 18  # approx in character heights, same as tmargin unit
    h = NORMAL_HEIGHT * plotdef.y_scale - tmargin - 1  # subtract 1 for xtics
    scale = h / NORMAL_HEIGHT
    scale = 1 / scale

    # calculate the position where the label is right aligned in the plot
    xpos = -0.005 * 28 / plotdef.width

    gpi = ""
    depth_sizes = treeutil.get_depth_sizes(tree)
    _, _, n_depth, _ = collectionutil.get_tree_details(tree)
    first_titlelabel = {}

    def branch(treenode, x, depth, width):
        nonlocal first_titlelabel, gpi
        fontsize = max(8, min(10, 11 - depth_sizes[depth] / (pow(plotdef.x_scale, 4) * 12)))

        ypos = 1 + (0.04 + 0.04 * (n_depth - depth - 1)) * scale

        if treenode['titlelabel'] != '' and depth not in first_titlelabel:
            first_titlelabel[depth] = False
            gpi += """
                set label \"""" + treenode['titlelabel'] + """:\" at \\
                    graph """ + str(xpos) + """, \\
                    graph """ + str(ypos) + """ \\
                    font ',""" + str(fontsize) + """pt' \\
                    tc rgb 'black' right
                """

        gpi += """
            set label \"""" + treenode['title'] + """\" at \\
                first """ + str(x) + """, \\
                graph """ + str(ypos) + """ \\
                font ',""" + str(fontsize) + """pt' \\
                tc rgb 'black' left
            """

    treeutil.walk_tree_reverse(tree, branch)

    xlabel = collectionutil.get_xlabel(tree)
    if xlabel is not None:
        ypos = -.06 * scale
        gpi += """
            set label \"""" + xlabel + """:\" at \\
                graph """ + str(xpos) + """, \\
                graph """ + str(ypos) + """ \\
                font ',10pt' \\
                tc rgb 'black' right
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


def component_container(component, tree, plotdef):
    _, _, n_depth, n_nodes = collectionutil.get_tree_details(tree)

    show_labels = not 'hide_labels' in component or not component['hide_labels']

    tmargin = 1
    if show_labels:
        tmargin += .7 * n_depth
    if 'key_rows' in component and component['key_rows'] > 0:
        tmargin += 1.5 + 1.1 * (component['key_rows'] - 1)

    r = ("rotate by %s" % plotdef.rotate_xtics) if plotdef.rotate_xtics else ""
    gpi = """
        unset bars
        set xtic """ + r + """ font ',""" + str(max(8, min(10, 15 - n_nodes / 18))) + """'
        set key above
        set xrange [-2:""" + str(n_nodes + 1) + """]
        set boxwidth 0.2
        set tmargin """ + str(tmargin) + """
        set lmargin 13
        """

    if plotdef.custom_xtics:
        gpi += """
            # add xtics below, the empty list resets the tics
            set xtics ()
            """

        def leaf(subtree, is_first_set, x):
            nonlocal gpi
            gpi += """
                set xtics add (""" + collectionutil.make_xtics(subtree, x, plotdef.x_axis) + """)
                """

        treeutil.walk_leaf(tree, leaf)

    if show_labels:
        gpi += plot_labels(tree, plotdef, component, tmargin)

    gpi += component['gpi']

    gpi += """
        unset logscale y
        unset label
        """

    component['gpi'] = gpi
    return component


def build_plot(tree, x_axis=PlotAxis.CATEGORY, components=None,
        lines_at_x_offset=None, x_scale=1, y_scale=1, rotate_xtics=-65):
    """
    Plot the collection tree provided using the provided components
    """

    if lines_at_x_offset is None:
        lines_at_x_offset = []
    if components is None:
        components = []

    class Plotdef:
        pass

    plotdef = Plotdef()
    plotdef.x_axis = x_axis
    plotdef.x_scale = x_scale
    plotdef.y_scale = y_scale
    plotdef.rotate_xtics = rotate_xtics
    plotdef.width = plotdef.x_scale * 21
    plotdef.custom_xtics = PlotAxis.is_custom_xtics(plotdef.x_axis)

    gpi = plot_header()
    gpi += plot_title(tree, len(components))

    def leaf_hook(subtree, is_first_set, x):
        nonlocal gpi
        for xoffset in lines_at_x_offset:
            gpi += line_at_x_offset(x, xoffset, subtree, plotdef.x_axis)

    for component in components:
        res = component_container(
            component(tree, plotdef, leaf_hook),
            tree,
            plotdef,
        )
        gpi += res['gpi']

    gpi += """
        unset multiplot"""

    return {
        'gpi': gpi,
        'width': '%fcm' % plotdef.width,
        'height': '%fcm' % (plotdef.y_scale * COMPONENT_HEIGHT * len(components)),
    }
