import os.path
from plumbum import local
import re

from . import treeutil
from ..testenv import read_metadata


def add_plot(gpi):
    """
    Remove trailing comma from plot command because gnuplot complains about it
    (We use the trailing comma to easier build plot commands)
    """
    return re.sub(r',(\s*\\?\s*)$', '\g<1>', gpi)


def add_scale(y_logarithmic, range_from='0', range_from_log='1', range_to='1<*', range_to_log=None):
    if y_logarithmic:
        if range_to_log is None:
            range_to_log = '*'
        return """
            set logscale y
            set yrange [""" + range_from_log + """:""" + range_to_log + """]
            """
    else:
        return """
            set yrange [""" + range_from + """:""" + range_to + """]
            """

def plot_header():
    return """
        set key spacing 1.3
        set grid xtics ytics ztics lw 1 lc rgb 'black'

        # from https://github.com/aschn/gnuplot-colorbrewer
        # line styles for ColorBrewer Dark2
        # for use with qualitative/categorical data
        # provides 8 dark colors based on Set2
        # compatible with gnuplot >=4.2
        # author: Anna Schneider

        # line styles
        set style line 1 lc rgb '#1B9E77' # dark teal
        set style line 2 lc rgb '#D95F02' # dark orange
        set style line 3 lc rgb '#7570B3' # dark lilac
        set style line 4 lc rgb '#E7298A' # dark magenta
        set style line 5 lc rgb '#66A61E' # dark lime green
        set style line 6 lc rgb '#E6AB02' # dark banana
        set style line 7 lc rgb '#A6761D' # dark tan
        set style line 8 lc rgb '#666666' # dark gray

        # palette
        set palette maxcolors 8
        set palette defined ( 0 '#1B9E77',\\
                              1 '#D95F02',\\
                              2 '#7570B3',\\
                              3 '#E7298A',\\
                              4 '#66A61E',\\
                              5 '#E6AB02',\\
                              6 '#A6761D',\\
                              7 '#666666' )

        """


def generate_hierarchy_data_from_folder(folder):
    """
    Generate a dict that can be sent to CollectionPlot by analyzing the directory

    It will look in all the metadata stored while running test
    to generate the final result
    """

    def parse_folder(subfolder):
        if not os.path.isdir(subfolder):
            raise Exception('Non-existing directory: %s' % subfolder)

        metadata_kv, metadata_lines = read_metadata(subfolder + '/details')

        if 'type' not in metadata_kv:
            raise Exception('Missing type in metadata for %s' % subfolder)

        if metadata_kv['type'] in ['collection']:
            node = {
                'title': metadata_kv['title'] if 'title' in metadata_kv else '',
                'subtitle': metadata_kv['subtitle'] if 'subtitle' in metadata_kv else '',
                'titlelabel': metadata_kv['titlelabel'] if 'titlelabel' in metadata_kv else '',
                'children': []
            }

            for metadata in metadata_lines:
                if metadata[0] == 'sub':
                    node['children'].append(parse_folder(subfolder + '/' + metadata[1]))

        elif metadata_kv['type'] == 'test':
            node = {
                'testcase': subfolder
            }

        else:
            raise Exception('Unknown metadata type %s' % metadata_kv['type'])

        return node

    root = parse_folder(folder)
    return root


def export(output_file, gpi_def):
    """
    Export a built plot to file
    """
    gpi = gpi_def['gpi']
    size = '%s,%s' % (gpi_def['width'], gpi_def['height'])

    gpi = """
        reset
        set terminal pdfcairo font 'Times-Roman,12' size """ + size + """
        set output '""" + output_file + """.pdf'
        """ + gpi

    # clean up whitespace at beginning of lines
    gpi = re.sub(r'^[\t ]+', '', gpi, 0, re.MULTILINE)

    with open(output_file + '.gpi', 'w') as f:
        f.write(gpi)

    local['gnuplot'][output_file + '.gpi'].run(stdin=None, stdout=None, stderr=None, retcode=None)


class PlotAxis:
    """
    Different ways to display x axis in each test
    """
    LOGARITHMIC = 'log'  # will generate xtics
    LOGARITHMIC_XTICS = 'log_xtics'  # will use provided xtics
    LINEAR = 'linear'  # will generate xtics
    LINEAR_XTICS = 'linear_xtics'  # will use provided xtics
    CATEGORY = 'category_xtics'  # will use provided xtics

    @staticmethod
    def is_custom_xtics(x_axis):
        return 'xtics' not in x_axis

    @staticmethod
    def is_logarithmic(x_axis):
        return 'log' in x_axis

    @staticmethod
    def is_linear(x_axis):
        return 'linear' in x_axis
