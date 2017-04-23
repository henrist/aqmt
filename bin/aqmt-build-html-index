#!/usr/bin/env python3
#
# This scripts generates an index.html file with links to all the
# individual flow plots in a test.

import argparse

from aqmt.plot import generate_hierarchy_data_from_folder, reorder_levels
from aqmt.testcollection import build_html_index


def command_parse(args):
    tree = reorder_levels(
        generate_hierarchy_data_from_folder(args.folder),
        level_order=[] if args.order == '' else [int(x) for x in args.order.split(',')],
    )

    out = build_html_index(tree, args.folder)

    with open(args.folder + '/index.html', 'w') as f:
        f.write(out)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('folder', help='directory containing collections to include')
    parser.add_argument('-o', '--order', help='sequence for order of levels', default='')
    parser.set_defaults(func=command_parse)

    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()
