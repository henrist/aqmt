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

import pprint
import sys

def plot_folder_compare(folder, swap_levels=None, x_axis=PlotAxis.CATEGORY, components=None):
    if components is None:
        components = [
            collection_components.utilization_queues(),
            collection_components.utilization_tags(),
            collection_components.queueing_delay(),
            collection_components.drops_marks(),
        ]

    if swap_levels is None:
        swap_levels = []

    export(
        folder + '/comparison',
        collection.build_plot(
            generate_hierarchy_data_from_folder(folder, swap_levels),
            x_axis=x_axis,
            components=components,
        )
    )

    print('Plotted comparison of %s' % folder)


def plot_folder_flows(folder, swap_levels=None, components=None):
    if swap_levels is None:
        swap_levels = []

    if components is None:
        components = [
            flow_components.utilization_queues(),
            flow_components.rate_per_flow(),
            flow_components.queueing_delay(),
            #flow_components.queueing_delay(y_logarithmic=True),
            flow_components.drops_marks(),
            #flow_components.drops_marks(y_logarithmic=True),
        ]

    tree = generate_hierarchy_data_from_folder(folder, swap_levels)
    folders = collectionutil.get_all_testcases_folders(tree)

    if len(folders) > 0:
        export(
            '%s/analysis_merged' % folder,
            flow.build_multiple_plot(folders, components)
        )

        print('Plotted merge of %s' % folder)


def plot_test(folder, components=None):
    if components is None:
        components = [
            flow_components.utilization_queues(),
            flow_components.rate_per_flow(),
            flow_components.queueing_delay(),
            #flow_components.queueing_delay(y_logarithmic=True),
            flow_components.drops_marks(),
            #flow_components.drops_marks(y_logarithmic=True),
        ]

    export(
        folder + '/analysis',
        flow.build_plot(folder, components),
    )

    print('Plotted %s' % folder)


def plot_tests(folder):
    tree = generate_hierarchy_data_from_folder(folder)

    for testcase_folder in collectionutil.get_all_testcases_folders(tree):
        plot_test(testcase_folder)
