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
* `example.py` is an example of using the test framework

### Using the framework

1. A `TestEnv` object is created defining some variables that is used
   for the tests, such as if existing tests should be rerun and the
   verbose level.
2. A main `TestCollection` is created defining where results will be
   stored and the title for all tests run inside it. The `TestEnv`
   object is injected when instanced.
3. Zero, one or multiple `TestCollection` objects are "chained" to form
   a hierarchy of test parameters. This is usually done in a loop.
4. In the deepest `TestCollection` one or more tests are run by calling
   `run_test` on the last `TestCollection` object. As arguments to this
   method call a function reference that defines the actual test/traffic,
   a `Testbed` object representing the testbed configuration that will be
   provisioned, a tag that distinguish the test from others in the same depth
   and optionally a title and titlelabel that add labels for this test in
   the plots.
5. After each `TestCollection` is finished with its work we call the `plot`
   method of its object to generate plots in its directory.

When the function reference with `run_test` is called, it will be given
an argument object of `TestCase`, which contains different traffic generation
methods that can be called to issue traffic.

For each test different metrics are collected and stored in individual files
in the individual test directory. Also a special file `details` contains the
configuration used to run this test. These files are read when the plotting
is generated.

#### Example test

Look at `example.py` for a implementation of a simple test.

See `../docker` for an example of how to run this test using Docker.

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
6. Build the traffic analyzer programs: `cd ../traffic_analyzer; make`

### Running a test

The tests are initiated from the AQM-node.

1. Modify `test.py` as desired
2. Start a tmux session (run `tmux`) - to exit it you can type 'exit' - you
   need tmux to run interactive tests (showing progress). If you have problems
   exiting try `ctrl+b x`.
3. `TEST_INTERACTIVE=1 ./test.py`

When test is complete, look in `results` for graphs.

## Plotting

The test framework can also perform plotting after each test. To customize
plotting see `plot.py`.

When chaining `TestCollection` objects the result is a folder tree that
represents the same chain. This chain also represents the grouping in the
plots, and can be manipulated to change how tests are grouped in the plot.

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
