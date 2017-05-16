"""
Module for manipulating the tree structure of collections

Definitions:
- Tree: the root node being handled)
- Branch: a branch inside the tree that contains other collections)
- Leaf branch: the last branch that contains test collections

Example tree:

    Abstract view:

                             root                 ("root", "tree", "branch", "collection")
                         /          \             (root contains plot title)
                         |          |
                    (possible more levels)        ("branch", "collection")
                        /            \
     linkrate:    10 mbit            20 mbit      ("branch", "leaf branch", "collection")
                 /       \          /       \
     rtt:      2 ms     10 ms     2 ms     10 ms  ("collection", "leaf collection")
                |        |         |        |     (only one collection inside leaf branches)
                |        |         |        |
               test     test      test     test   ("test")
                                                 (only one test in leaf collections)

    The reason for having tests as children similar as normal
    branches is to allow easy manipulation of the tree, e.g.
    swapping levels.

    Actual structure:

    {
        'title': 'Plot title',
        'titlelabel': '',
        'subtitle': '',
        'children': [
            {
                'title': '10 Mb/s',
                'titlelabel': 'Linkrate',
                'subtitle': '',
                'children': [
                    {
                        'title': '2',
                        'titlelabel': 'RTT',
                        'subtitle': '',
                        'children': [
                            {'testcase': 'results/plot-tree/linkrate-10/rtt-2/test'}
                        ],
                    },
                    {
                        'title': '10',
                        'titlelabel': 'RTT',
                        'subtitle': '',
                        'children': [
                            {'testcase': 'results/plot-tree/linkrate-10/rtt-10/test'}
                        ],
                    },
                ],
            },
            {
                'title': '20 Mb/s',
                'titlelabel': 'Linkrate',
                'subtitle': '',
                'children': [
                    {
                        'title': '2',
                        'titlelabel': 'RTT',
                        'subtitle': '',
                        'children': [
                            {'testcase': 'results/plot-tree/linkrate-20/rtt-2/test'}
                        ]
                    },
                    {
                        'title': '10',
                        'titlelabel': 'RTT',
                        'subtitle': '',
                        'children': [
                            {'testcase': 'results/plot-tree/linkrate-20/rtt-10/test'}
                        ]
                    },
                ],
            },
        ],
    }

X offsets:
    X offsets in the tree are increased so that they cause natural
    gaps betweep test branches. So between branches at a deep level
    there is a small gap, while close to the root branch there will
    be more gap.

    In the example above the tests would have the following x offsets
      - test 1: 0
      - test 2: 1
      - test 3: 3 (new branch, so x is increased to form a gap)
      - test 4: 4
"""

from collections import OrderedDict


def get_depth_sizes(tree):
    """
    Calculate the number of branches at each tree level
    """
    depths = {}

    def check_node(item, x, depth):
        if depth not in depths:
            depths[depth] = 0
        depths[depth] += 1

    walk_tree(tree, check_node)
    return depths


def walk_leaf(tree, fn):
    """
    Walks the tree and calls fn for every leaf branch

    The arguments to fn:
    - object: the leaf branch
    - bool: true if first leaf branch in tree
    - number: the x offset of this leaf branch
    """

    x = 0
    is_first = True

    def walk(branch):
        nonlocal is_first, x

        if len(branch['children']) == 0:
            return

        first_child = branch['children'][0]

        is_leaf_branch = 'testcase' in branch['children'][0]['children'][0]
        if is_leaf_branch:
            fn(branch, is_first, x)
            is_first = False
            x += len(branch['children'])

        # or is it a collection of collections
        else:
            for item in branch['children']:
                walk(item)

        x += 1

    walk(tree)


def walk_tree_reverse(tree, fn):
    """
    Walks the tree and calls fn for every branch in reverse order

    The arguments to fn:
    - object: the branch
    - number: the x offset of this branch
    - number: depth of this branch, 0 being root
    - number: the number of tests inside this branch
    """
    x = 0

    def walk(branch, depth=0):
        nonlocal x

        is_leaf_branch = 'testcase' in branch['children'][0]['children'][0]
        if is_leaf_branch:
            x += len(branch['children'])

        # or else it is a non-leaf branch
        else:
            for item in branch['children']:
                y = x
                walk(item, depth + 1)
                fn(item, y, depth, x - y)

        x += 1

    walk(tree, 0)


def walk_tree(tree, fn, include_leaf_collection=False):
    """
    Walks the tree and calls fn for every branch, and also for every
    leaf collection if include_leaf_collection is True.

    The arguments given to fn:
    - object: the collection
    - number: the x offset related to number of tests/levels
    - number: depth of this collection, 0 being root
    """
    x = 0

    def walk(collection, depth=0):
        nonlocal x

        for subcollection in collection['children']:
            fn(subcollection, x, depth)

            if include_leaf_collection:
                is_leaf_collection = 'testcase' in subcollection['children'][0]
                if is_leaf_collection:
                    x += 1
                    continue

            # If input to walk_tree was a leaf branch, we can't look
            # if we have  leaf branch inside
            elif 'children' not in subcollection['children'][0]:
                continue

            else:
                is_leaf_branch = 'testcase' in subcollection['children'][0]['children'][0]
                if is_leaf_branch:
                    x += len(subcollection['children']) + 1
                    continue

            walk(subcollection, depth + 1)

        x += 1

    walk(tree)


def swap_levels(tree, level=0):
    """
    Rearrange vertical position of elements in the tree.

    This swaps collections in the tree so their level
    in the tree is changed.

    For the plotting, this will change the way tests
    are grouped and presented.
    """

    if level > 0:
        def walk(branch, depth):
            if len(branch['children']) == 0:
                return

            # is this a set of tests?
            if 'testcase' in branch['children'][0]:
                return

            for index, item in enumerate(branch['children']):
                if depth + 1 == level:
                    branch['children'][index] = swap_levels(item)
                else:
                    walk(item, depth + 1)

        walk(tree, 0)
        return tree

    titles = []

    def check_level(node, x, depth):
        nonlocal titles
        if depth == 1 and node['title'] not in titles:
            titles.append(node['title'])

    walk_tree(tree, check_level, include_leaf_collection=True)

    if len(titles) == 0:
        return tree

    new_children = OrderedDict()
    parent = None

    def build_swap(node, x, depth):
        nonlocal parent, new_children
        if depth == 0:
            parent = node
        elif depth == 1:
            parentcopy = dict(parent)
            if node['title'] in new_children:
                new_children[node['title']]['children'].append(parentcopy)
            else:
                childcopy = dict(node)
                childcopy['children'] = [parentcopy]
                new_children[node['title']] = childcopy

            parentcopy['children'] = node['children']

    walk_tree(tree, build_swap, include_leaf_collection=True)

    tree['children'] = [val for key, val in new_children.items()]
    return tree


def build_swap_list(level_order):
    """
    Build a list of levels that should be swapped to achieve
    a specific ordering of levels.
    """

    # assert the values
    distinct = []
    for val in level_order:
        if val in distinct:
            raise Exception("Duplicate value: %s" % val)
        if not isinstance(val, int):
            raise Exception("Invalid type: %s" % val)
        if val < 0:
            raise Exception("Value out of bounds: %s" % val)
        distinct.append(val)

    # fill any missing values
    for i in range(max(level_order)):
        if i not in level_order:
            level_order.append(i)

    # work through the list and build a swap list
    swap_list = []
    to_process = list(range(len(level_order)))  # same as an sorted version of the list
    for i in range(len(level_order)):
        # find offset of this target
        to_swap = 0
        while level_order[i] != to_process[to_swap]:
            to_swap += 1

        # pull up the target so it become the current level
        for x in range(to_swap):
            swap_list.append(i + (to_swap - x - 1))

        # remove the level we targeted
        to_process.remove(level_order[i])

    return swap_list


def reorder_levels(tree, level_order=None):
    """
    Order the tree based on an ordering of levels
    (number of branches in height in the tree)

    E.g. a tree of 3 levels where we want to reorder the levels
    so that the order is last level, then the first and then the
    second:

      level_order=[2,0,1]

    Example reversing the order of three levels:

      level_order=[2,1,0]
    """

    if level_order is None or len(level_order) == 0:
        return tree

    # get the depth of the tree only counting branches
    levels = len(get_depth_sizes(tree))

    swap_list = build_swap_list(level_order)
    if len(swap_list) > 0 and max(swap_list) >= levels:
        raise Exception("Out of bound level: %d. Only have %d levels" % (max(swap_list), levels))

    # apply the calculated node swapping to the tree
    for level in swap_list:
        tree = swap_levels(tree, level)

    return tree


def skip_levels(tree, number_of_levels):
    """
    Select the left node number_of_levels deep and
    return the new tree
    """

    # allow to select specific branches in a three instead of default first
    if type(number_of_levels) is list:
        for branch in number_of_levels:
            tree = tree['children'][branch]
        return tree

    while number_of_levels > 0:
        tree = tree['children'][0]
        number_of_levels -= 1

    return tree
