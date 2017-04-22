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
from .treeutil import reorder_levels

import pprint
import sys

def plot_folder_compare(folder, level_order=None, components=None, **kwargs):
    if components is None:
        components = [
            collection_components.utilization_queues(),
            collection_components.utilization_tags(),
            collection_components.queueing_delay(),
            collection_components.drops_marks(),
        ]

    export(
        folder + '/comparison',
        collection.build_plot(
            reorder_levels(
                generate_hierarchy_data_from_folder(folder),
                level_order,
            ),
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


def plot_test(folder, components=None, **kwargs):
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
        folder + '/analysis',
        flow.build_plot(folder, components, **kwargs),
    )

    print('Plotted %s' % folder)


def plot_tests(folder):
    tree = generate_hierarchy_data_from_folder(folder)

    for testcase_folder in collectionutil.get_all_testcases_folders(tree):
        plot_test(testcase_folder)
