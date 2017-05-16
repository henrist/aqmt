"""
Plot library for AQM test framework
"""

__title__ = 'Plot library for AQM test framework'
__author__ = 'Henrik Steen'

from . import collection_components
from . import collection
from . import flow
from . import flow_components
from .common import PlotAxis, generate_hierarchy_data_from_folder, export
from .treeutil import reorder_levels, skip_levels as tree_skip_levels

import pprint
import sys

def plot_folder_compare(folder, name='comparison',
        level_order=None, skip_levels=0,
        components=None, title=None, subtitle=None, **kwargs):
    """
    - If title and/or subtitle is given they will override the value
      in the tree. If set to False, no title will be given on the plot.
    """

    if components is None:
        components = [
            collection_components.utilization_queues(),
            collection_components.utilization_tags(),
            collection_components.queueing_delay(),
            collection_components.drops_marks(),
        ]

    tree = tree_skip_levels(
        reorder_levels(
            generate_hierarchy_data_from_folder(folder),
            level_order,
        ),
        skip_levels,
    )

    if title is not None:
        tree['title'] = None if title == False else title

    if subtitle is not None:
        tree['subtitle'] = None if subtitle == False else subtitle

    export(
        folder + '/' + name,
        collection.build_plot(
            tree,
            components=components,
            **kwargs,
        )
    )

    print('Plotted comparison of %s' % folder)


def plot_folder_flows(folder, level_order=None, components=None, **kwargs):
    if components is None:
        components = [
            flow_components.utilization_queues(),
            flow_components.rate_per_flow(),
            flow_components.rate_per_flow(y_logarithmic=True),
            flow_components.queueing_delay(),
            flow_components.queueing_delay(y_logarithmic=True),
            flow_components.drops_marks(),
            flow_components.drops_marks(y_logarithmic=True),
        ]

    tree = reorder_levels(
        generate_hierarchy_data_from_folder(folder),
        level_order,
    )
    folders = collectionutil.get_all_testcases_folders(tree)

    if len(folders) > 0:
        export(
            '%s/analysis_merged' % folder,
            flow.build_multiple_plot(folders, components, **kwargs)
        )

        print('Plotted merge of %s' % folder)


def plot_test(folder, name='analysis', components=None, **kwargs):
    if components is None:
        components = [
            flow_components.utilization_queues(),
            flow_components.rate_per_flow(),
            flow_components.rate_per_flow(y_logarithmic=True),
            flow_components.window(),
            flow_components.window(y_logarithmic=True),
            flow_components.queueing_delay(),
            flow_components.queueing_delay(y_logarithmic=True),
            flow_components.drops_marks(),
            flow_components.drops_marks(y_logarithmic=True),
        ]

    export(
        folder + '/' + name,
        flow.build_plot(folder, components, **kwargs),
    )

    print('Plotted %s' % (folder + '/' + name))


def plot_tests(folder):
    tree = generate_hierarchy_data_from_folder(folder)

    for testcase_folder in collectionutil.get_all_testcases_folders(tree):
        plot_test(testcase_folder)


def hide_labels(component):
    """
    Higher order component to disable labels
    """
    def plot(*args, **kwargs):
        result = component(*args, **kwargs)
        result['hide_labels'] = True
        return result

    return plot
