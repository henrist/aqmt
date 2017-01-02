# Test framework for AQMs

This folder contains scripts that can be used to write tests to evaluate different AQMs and configurations.

It can also run on one single Linux-machine using a special Docker-setup.
Look in `../docker/` for a quick quide.

## Framework overview

* `common.sh` does the actual system modifications
* `framework/test_framework.py` is the framework the uses `common.sh` to
  setup the testbed and which actually runs the tests
* `framework/plot.py` does all plotting
* `vars.sh` makes sure we have all environment variables set so the
  scripts actually work
* `test.py` is examples of using the test framework

## Testbed structure

```
           +---------+    +--------+
Client A---| Clients |____|  AQM   |---Server A
Client B---| switch  |    | server |---Server B
           +---------+    +--------+
```

## Running on a real testbed with multiple machines

### System setup

Prerequirements on AQM-machine:

* `sudo apt-get install iperf gnuplot python3 python3-pip speedometer tmux`
* `pip3 install numpy plumbum`

Prerequirements on other clients and servers:

* `sudo apt-get install iperf`

Setup:

1. Create an environment configuration file, use `simula_testbed.env` as a
   template. This file is sourced by `vars.sh` later.
2. Set up SSH-keys so the AQM-machine can SSH into all the nodes without
   using password. It will SSH into the root user, so make sure the public
   key is added to `/root/.ssh/authorized_keys` on all nodes.
3. Distribute variables and programs to the clients and servers by running
   `./update_nodes_data.sh`
4. Build the custom iproute2 suite (needed for our custom schedulers):
   * `git submodule init && git submodule update`
   * `cd iproute2-l4s`
   * `make` (the binary will be added to PATH by `vars.sh` later)
5. Build and load the schedulers: `../load_sch.sh` (has to be done every time
   the AQM-node is rebooted).

### Running a test

The tests are initiated from the AQM-node.

1. Modify `test.py` as desired
2. Start a tmux session (run `tmux`) - to exit it you can type 'exit' - you
   need tmux to run interactive tests (showing progress). If you have problems
   exiting try `ctrl+b x`.
3. `TEST_INTERACTIVE=1 ./test.py`

When test is complete, look in `results` for graphs.

## Increasing the rmem and wmem tcp sizes

On our test machine the default rmem and wmem values equals a maximum
TCP window size of approx 965 packets of 1500b MTU. (It's limited of the wmem,
allthough rmem defaults to approx 4780 packets.) On a 1 gigabit link latency
above 11,6 ms will cause the utilization to drop.

To increase rmem and wmem:

1. Source `vars.sh` to know all nodes: `. vars.sh`
2. Run e.g. `./utils/set_sysctl_tcp_mem.sh 5000` to allow a TCP window up to
   approx. 5000 packets.

## Monitoring while testing

Usefull tools for monitoring:

Run on different nodes:

- `watch -n 1 ./views/show_setup.sh -v $IFACE_CLIENTS` - watch qdisc stats
  for this interface - replace `$IFACE_CLIENTS` with the actual interface on
  the node.

Run on the AQM-node:

- `watch -c -n 1 ./views/views/ss.sh` - watch socket statistics on all nodes
  for traffic within the test port range
