import socket
import os.path

# src: http://stackoverflow.com/a/40655575/4471194
def memoize(function):
    from functools import wraps

    memo = {}

    @wraps(function)
    def wrapper(*args):
        if args in memo:
            return memo[args]
        else:
            rv = function(*args)
            memo[args] = rv
            return rv
    return wrapper

@memoize
def hostname():
    """
    Get the hostname we are on. If we are running inside Docker
    we will have a special file we can look for. If this is missing,
    use the known hostname.
    """

    hostname = ''
    if os.path.isfile('/tmp/dockerhost-hostname'):
        with open('/tmp/dockerhost-hostname', 'r') as f:
            hostname = f.read().strip().split()[0]

    if hostname == '':
        hostname = socket.gethostname()

    return hostname
