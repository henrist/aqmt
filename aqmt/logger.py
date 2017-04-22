"""
This module contains our logger component.
"""

from datetime import datetime
import os

TRACE = 4
DEBUG = 3
INFO = 2
WARN = 1
ERROR = 0

NAME_TABLE = {
    'TRACE': TRACE,
    'DEBUG': DEBUG,
    'INFO': INFO,
    'WARN': WARN,
    'ERROR': ERROR,
}

LEVEL_TABLE = {
    TRACE: 'TRACE',
    DEBUG: 'DEBUG',
    INFO: 'INFO',
    WARN: 'WARN',
    ERROR: 'ERROR',
}


def get_level_from_name(level_name, default):
    if level_name in NAME_TABLE:
        return NAME_TABLE[level_name]
    return default

print_level = get_level_from_name(
    os.environ['LOG_LEVEL'] if 'LOG_LEVEL' in os.environ else '',
    INFO
)
file_level = TRACE
logfile = os.environ['LOG_FILE'] if 'LOG_FILE' in os.environ else 'aqmt.log'


def get_level_name(level):
    if level in LEVEL_TABLE:
        return LEVEL_TABLE[level]
    return 'UNKNOWN'


def trace(msg):
    log(TRACE, msg)


def debug(msg):
    log(DEBUG, msg)


def info(msg):
    log(INFO, msg)


def warn(msg):
    log(WARN, msg)


def error(msg):
    log(ERROR, msg)


def log(level, msg):
    """
    Log a message to stdout and/or logfile
    """
    if level <= print_level:
        print(msg)

    if level <= file_level and logfile is not None:
        with open(logfile, 'a') as f:
            level_name = get_level_name(level)
            prefix = '%s %7s: ' % (datetime.now().isoformat(), level_name)
            f.write(prefix_multiline(prefix, msg, '\n'))


def prefix_multiline(prefix, msg, append=''):
    return prefix + msg.replace('\n', '\n' + ' ' * len(prefix)) + append
