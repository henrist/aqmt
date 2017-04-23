# Test framework for AQMs - Python package

This is the Python package containing the framework for testing
AQMs and congestion controls.

It also contains a few programs that requires compiling and do the
capturing of traffic and the calculations.

See that parent directory for instructions for how to run this
on a testbed.

## Framework overview

Main parts of the framework:

- *Constructing all the test parameters and initiating a test*: This
  is the core functionality of the Python scripts. Tests are written
  quite declerative, while still gaining a lot of customization.
  More about this below.
- *Modification of the network configuration:* This is abstracted into
  `aqmt-testbed.sh` in the root `bin` folder, and is called by the
  framework.
- *Traffic capturing/analysis:* The `ta` subfolder contains a program
  that uses pcap to capture the network traffic. The AQM will modify
  a special header in the TCP packet adding details about queueing
  delay and number of dropped packets, which the analyzer decodes.
  The result of this is the core basis for further analysis/plotting.
- *Futher analyzing the raw test results:* Various `calc_*` scripts/programs
  reads the results from the analyzer and generates various statistics
  used for plotting.
- *Plotting the results:* The plotting logic is seperated into a subpackage
  located in the `plot` folder.

## Test results

Test results are saved inside a directory of your choice when you run
a test. The structure of this directory will be so each "class" of parameters
will be in subfolder, forming a hierarchy.

E.g. if you are testing a combination of different RTT and bitrates, the
results might have a folder structure such as:

```
mytest/
  rtt-10/
    bitrate-50/
      test/
    bitrate-80/
      test/
  rtt-30/
    bitrate-50/
      test/
    bitrate-80/
      test/
```

In each of these directories there will be a special file `details`
which contains metadata about the tests that were run, and is used
to rebuild the test hierarchy later on and add the different titles
for the different locations in the hierarchy.

This hierarchy is a core feature of the framework, and many objects
you will see follow this, e.g. `TestCollection` and all the tree
utilities in the plot scripts.

A powerfull feature of this structure is the ability to use all sorts
of tree manipulation techniques after the test is run, e.g. to regroup
the parameters.

The `plot/treeutil.py` module contains a few comments that describe the
tree that us build white plotting.

## Constructing a test definition

See the example in https://github.com/henrist/aqmt-example for an initial
view of how to use the framework.

In general, a test definition consists of middlewares, which causes branches
in the tests (e.g. different RTTs) and alters the testbed definition,
before giving control to the next middleware.

At the end of the middlewares, the testbed is configured as defined
and a test is executed.

You could compare this as a dynamic tree where all nodes are walked,
and the actual test being the leaf nodes.

### Middlewares/steps

All the included middlewares are located in `steps.py`. Feel free to write
your own and leave it in your own test script.

There are two ways a middleware should work:

- Create one or more branches in the tree. This will cause new folders
  in the test results.
- Don't create a branch, but do other usefull stuff at that location
  in the tree. Plotting is an example of this. As well is the build in
  step to skip a tree edge if a specific condition is met.

### Configuring the testbed

The testbed itself is defined on the `Testbed` instance that is
available in the middlewares. Have a look at [`testbed.py`](./testbed.py)
for what you can change.

### The test itself (the last step)

The last step works as follow:

- Before executed:
  - A `TestCase` object is created representing this test
  - The testbed is configured
  - Traffic analyzer starts to capture data
- Then the test function you have provided will be run
  - It should generate data
- After the traffic analyzer has finished capturing data, the test
  will be killed.
- The individual test is then analyzed and plotted for itself.
  You will find this plot by going deep in the result folder.
- Control is given back to the previous middleware, and
  everything continues as before.

### Generating traffic

When a test is executed, it is up to control the traffic generation.

We have provided a set of traffic scripts. Look in `traffic.py`
for the complete list. The example implementation should tell you how
this is used. Feel free to write your own traffic generator.

Note that all traffic generation is using a predefined port.
This is used to classify all the flows we are capturing, so
not everything looks as one flow, and so we can actually group
and set title to different flows.

## Plotting

The test framework can also perform plotting after each test. You can use
the provided plot middlewares from `steps.py`, which uses the included
plot scripts inside the `plot.py` package. You can also build your own
plot logic and include it as a middleware.

### Plotting a subset of a test

By changing the test definition you can remove parts of the test, and
rerun the test. If testdata already exists, it will not run the traffic
again, but use the existing data to plot again.

## Environment variables

### Enable interactive test

```
TEST_INTERACTIVE=1
```

### Change log level to console

```
LOG_LEVEL=TRACE
```

See `logger.py` for levels

### Don't ask for confirmation for running test

```
TEST_NO_ASK=1
```
