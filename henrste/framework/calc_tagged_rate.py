#!/usr/bin/env python3

# this file generates rate statistics for the different tagget traffic streams
#
# as all the test traffic uses different ports we don't need to worry
# about which nodes that sends traffic
#
# the results are saved to:
# - rate_tagged
# - rate_tagged_stats
# - util_tagged
# - util_tagged_stats

import numpy as np
import os
import re

DEFAULT_TAG = 'Other'


def generate_stats(numbers):
    if len(numbers) == 0:
        res = ['0', '0', '0', '0', '0', '0', '0', '0', '0']
    else:
        res = [
            np.average(numbers).astype('str'),
            '-',  # not used: np.std(numbers).astype('str'),
            np.min(numbers).astype('str'),
            np.percentile(numbers, 1, interpolation='lower').astype('str'),
            np.percentile(numbers, 25, interpolation='lower').astype('str'),
            np.percentile(numbers, 50, interpolation='lower').astype('str'),
            np.percentile(numbers, 75, interpolation='lower').astype('str'),
            np.percentile(numbers, 99, interpolation='lower').astype('str'),
            np.max(numbers).astype('str'),
        ]

    return ' '.join(res)


def save_tag_rates(folder, rates):
    with open(folder + '/derived/rate_tagged', 'w') as fall:
        fall.write('#sample rate\n')

        with open(folder + '/aggregated/rate_tagged_stats', 'w') as fstats:
            fstats.write('#tag average stddev min p1 p25 p50 p75 p99 max\n')

            first = True
            for tag, values in rates.items():
                if not first:
                    fall.write('\n\n')
                first = False
                fall.write('"%s"\n' % tag)

                for i, rate in enumerate(values):
                    fall.write('%d %d\n' % (i, rate))

                fstats.write('"%s" %s\n' % (tag, generate_stats(values)))


def save_tag_util(folder, rates, bitrate):
    with open(folder + '/derived/util_tagged', 'w') as fall:
        fall.write('#sample util\n')

        with open(folder + '/aggregated/util_tagged_stats', 'w') as fstats:
            fstats.write('#tag average stddev min p1 p25 p50 p75 p99 max\n')

            first = True
            for tag, values in rates.items():
                list_util = []

                if not first:
                    fall.write('\n\n')
                first = False
                fall.write('"%s"\n' % tag)

                for i, rate in enumerate(values):
                    util = rate / bitrate
                    list_util.append(util)

                    fall.write('%d %f\n' % (i, util))

                fstats.write('"%s" %s\n' % (tag, generate_stats(list_util)))


def get_rates(folder, flows, tags):
    """Map all known rates to the tag and aggregated rate"""

    rates = {DEFAULT_TAG: []}
    for tag in tags:
        rates[tag] = []

    n_samples = None  # will use the last one in following loop
    for ecntype in ['ecn', 'nonecn']:
        n_samples = 0
        with open(folder + '/ta/flows_rate_' + ecntype) as f:
            # 0 1000 6152397 3693860
            for line in f:
                n_samples += 1

                for i, rate in enumerate(line.split()[2:]):
                    tag = flows[ecntype][i]['tag']

                    if len(rates[tag]) < n_samples:
                        rates[tag].append(0)

                    rates[tag][n_samples - 1] += int(rate)

    # remove unknown if all is tagged
    if len(rates[DEFAULT_TAG]) == 0:
        rates.pop(DEFAULT_TAG)

    # make sure all lists are filled up
    # (in case no traffic is detected on a tag)
    for tag in tags:
        if len(rates[tag]) == 0:
            rates[tag] = [0] * n_samples

    return rates


def extract_properties(line):
    """Convert the line in the 'details' file to a map"""
    list = {}
    name = None

    for item in re.split(r'(?:^| )([^= ]+=)', line.strip()):
        if item.endswith('='):
            name = item[0:-1]
        elif name is not None:
            list[name] = item

    return list


def get_classification(folder):
    tags = set()
    classify = []

    with open(folder + '/details', 'r') as f:
        for line in f:
            if line.startswith('traffic='):
                properties = extract_properties(line)
                if 'tag' in properties:
                    tag = properties['tag']
                    tags.add(tag)

                    classify_by = 'client' if 'client' in properties else 'server'
                    classify.append({classify_by: properties[classify_by], 'tag': tag})

    return [list(tags), classify]


def get_bitrate(folder):
    with open(folder + '/details', 'r') as f:
        for line in f:
            if line.startswith('testbed_rate '):
                return int(line.split(' ')[1])

    raise Exception('Could not determine bitrate used in test')


def get_flows(folder, classify):
    flows = {'ecn': [], 'nonecn': []}
    for ecntype in ['ecn', 'nonecn']:
        with open(folder + '/ta/flows_' + ecntype) as f:
            for line in f:
                # TCP 10.25.2.21 5504 10.25.1.11 53898
                _type, srcip, srcport, dstip, dstport = line.split()

                # identify the tag
                tag = DEFAULT_TAG
                for item in classify:
                    if 'client' in item and item['client'] == dstport:
                        tag = item['tag']
                        break
                    elif 'server' in item and item['server'] == srcport:
                        tag = item['tag']
                        break

                flows[ecntype].append({
                    'flow': line.strip(),
                    'tag': tag
                })

    return flows


def process_test(folder):
    if not os.path.exists(folder + '/derived'):
        os.makedirs(folder + '/derived')

    if not os.path.exists(folder + '/aggregated'):
        os.makedirs(folder + '/aggregated')

    tags, classify = get_classification(folder)
    bitrate = get_bitrate(folder)
    flows = get_flows(folder, classify)

    rates = get_rates(folder, flows, tags)

    save_tag_rates(folder, rates)
    save_tag_util(folder, rates, bitrate)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: %s <test_folder>', sys.argv[0])
    process_test(sys.argv[1])
