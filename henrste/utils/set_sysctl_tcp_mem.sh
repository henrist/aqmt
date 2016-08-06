sysctl -w net.ipv4.tcp_rmem='4096 87380 8388608'
sysctl -w net.ipv4.tcp_wmem='4096 65536 8388608'

# default on DARASK-X250:
# rmem: 4096    87380   6291456
# wmem: 4096    16384   4194304
