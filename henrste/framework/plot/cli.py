#!/usr/bin/env python3

"""
This module provides a CLI that can be used to plot collections
manually.
"""

# add path to library root
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))

import argparse
import os.path

from framework.plot.common import PlotAxis
from framework.plot import collection_components
from framework.plot import plot_folder_compare, plot_folder_flows, plot_tests


def command_comparison(args):
    x_axis = PlotAxis.CATEGORY
    if args.logarithmic:
        x_axis = PlotAxis.LOGARITHMIC
    elif args.linear:
        x_axis = PlotAxis.LINEAR

    components = []
    if not args.nouq:
        components.append(collection_components.utilization_queues())

    if args.ut:
        components.append(collection_components.utilization_tags())

    components.append(collection_components.queueing_delay())
    components.append(collection_components.drops_marks())

    plot_folder_compare(
        args.folder,
        swap_levels=[] if args.swap == '' else [int(x) for x in args.swap.split(',')],
        x_axis=x_axis,
        components=components,
    )


def command_merge(args):
    plot_folder_flows(
        args.folder,
        swap_levels=[] if args.swap == '' else [int(x) for x in args.swap.split(',')],
    )


def command_plot_tests(args):
    plot_tests(args.folder)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help='sub-command help')

    parser_a = subparsers.add_parser('comparison', help='plot a comparison for collections')
    parser_a.add_argument('folder', help='directory containing collections to include')
    parser_a.add_argument('-s', '--swap', help='list of levels to swap', default='')
    parser_a.add_argument('--nouq', help='skip utilization plot for each queue', action='store_true')
    parser_a.add_argument('--ut', help='include utilization plot for each tag', action='store_true')
    axis = parser_a.add_mutually_exclusive_group()
    axis.add_argument('--logarithmic', help='plot X axis logarithmic instead of by category', action='store_true')
    axis.add_argument('--linear', help='plot X axis linearly instead of by category', action='store_true')
    parser_a.set_defaults(func=command_comparison)

    parser_b = subparsers.add_parser('merge', help='merge plots from multiple tests')
    parser_b.add_argument('folder', help='directory containing collections to include')
    parser_b.add_argument('-s', '--swap', help='list of levels to swap', default='')
    parser_b.set_defaults(func=command_merge)

    parser_c = subparsers.add_parser('tests', help='individual plots for tests')
    parser_c.add_argument('folder', help='directory containg collections to inclued')
    parser_c.set_defaults(func=command_plot_tests)

    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()
