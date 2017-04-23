# Test framework for AQMs

This framework allows you to evaluate an Active Queue Management
implementation, such as PIE (or your own). It focuses on the queue
that is built in the router and the number of drops it causes.
It is also Explicit Congestion Control (ECN) compatible,
comparing non-ECN against ECN flows.

Your only requirement is a computer running Linux 4.10 or newer
(or actually, you should be able to use this for 3.16 and newer,
see below), and that you have Docker installed.

We currently recommend using Ubuntu 17.04, as it includes the
4.10 kernel.

Docker is no hard requirement, but you need a physical testbed
of 5 machines with networking unless you use it.

## Testbed structure

This is the structure we use for the evaluation:

```
           +---------+    +--------+
Client A---| Clients |____|  AQM   |---Server A
Client B---| switch  |    | server |---Server B
           +---------+    +--------+
```

This is the structure used for test traffic. In addition there
is a management network that don't affect the tests.

## Example implementation

An example is provided in
https://github.com/henrist/aqmt-example

It should let you get started with your first results within 10
minutes if you already have Docker.

## Dependencies using Docker

See [docker](./docker/README.md) subfolder for more details how
you can use it with Docker.

See below for details for how to use this without Docker, e.g.
on a physical testbed infrastructure.

## Using the framework to write tests and analyze results

See [aqmt](./aqmt/README.md) subfolder.

## Using schedulers (qdiscs) in tests

We have a special requirements for all schedulers we will be testing.
We need to modify them so they will give us precise statistics about
delay and drops.

We are using the IPv4 ID field in the packets to signal queueing delay
and drop information. See [RFC6864](https://tools.ietf.org/html/rfc6864)
for more details about the ID field.

We have provided three implementations you can look at:

- https://github.com/henrist/aqmt-fq-codel-scheduler
- https://github.com/henrist/aqmt-pfifo-scheduler
- https://github.com/henrist/aqmt-pie-scheduler

## Provided tools

A number of tools are provided to ease monitoring.

To be run on the AQM machine:

- `aqmt-aqm-monitor-node`: Runs `aqmt-monitor-node` on a given node. E.g.
  `aqmt-aqm-monitor-node clienta`.
- `aqmt-aqm-monitor-setup`: Runs `aqmt-show-setup` periodically for the AQM
  interface.
- `aqmt-aqm-monitor-traffic`: Runs `speedometer` for the three interfaces
  on the AQM machine. Will visualize the traffic that is running.
- `aqmt-get-kernel-setup`: Will show you various ethernet and memory
  settings that is currently in effect.
- `aqmt-ss-stats`: Runs `ss` on clients/servers filtering test traffic.
  Can be used to investigate window sizes, memory configuration etc.

To be run on any machine:

- `aqmt-get-sysctl`: Show you the current rmem and wmem limits.
- `aqmt-kill-ssh-control-ports`: Removes the SSH control socket, can
  be used if the SSH connections become stale (you don't normally need this).
- `aqmt-monitor-iface-status`: Monitors the number of packets sent/received
  as well as number of drops on the interface level. If you have drops on the
  interface level, other limits (such as netem limit) drops packets!
- `aqmt-show-setup`: Dumps information from `tc` and `ip`.
  Run `aqmt-show-setup -h` for usage. Use it with `watch` to monitor
  interfaces, e.g.: `watch -n 0.5 aqmt-show-setup -v $IFACE_AQM` on
  a client/server.

Other utilities:

- `aqmt-reset-testbed`: Resets the testbed (removes the qdiscs, delay etc.)
  from the AQM machine.
- `aqmt-set-sysctl-tcp-mem`: See seperate section explaining.
- `aqmt-update-nodes-vars`: See seperate section explaining.

## Configuring the testbed outside a test

You can use the provided `configure-testbed.py` to set up the testbed
similar to what is done inside a test.

Use this if you want to experiment without having to run the test
framework.

When done, you can use `aqmt-reset-testbed` to remove the setup.
You will need to reset the testbed if you want to reload any
kernel modules. The framework resets before/after every test.

## Increasing the rmem and wmem tcp sizes

You normally don't need to do this.

On our test machine the default rmem and wmem values equals a maximum
TCP window size of approx 965 packets of 1500b MTU. (It's limited of the wmem,
allthough rmem defaults to approx 4780 packets.) On a 1 gigabit link, latency
above 11,6 ms will cause the utilization to drop.

To increase rmem and wmem to allow a TCP window up to approx. 5000 packets:

```bash
# from the AQM-machine
aqmt-set-sysctl-tcp-mem 5000
```

It will apply the change to all the machines.

## Vagrant and Ansible

This is work in progress where we want to use Vagrant to provision
a test environment (with Docker inside), so we have full control of the
host kernel.

https://www.vagrantup.com/docs/provisioning/ansible_local.html

## Running on a real testbed

Okay. So you don't trust Docker will give you good enough results,
or simply want everything to go over an physical environment.

The AQM-machine is the management node, where you need the framework,
define your environment and put your test scripts.

Required packages on the AQM-machine:

```bash
# on the AQM-machine
# (Ubuntu 16.10 has been used)

sudo apt install \
  ethtool \
  g++ \
  gnuplot \
  libpcap-dev \
  make \
  python3 \
  python3-pip \
  speedometer \
  tmux

sudo pip3 install \
  numpy \
  plumbum
```

The clients and servers also need any needed package for the traffic
generation you are going to use. E.g. if you want to use iperf, you need
iperf available on the machines.

For the example repository, we are using
https://github.com/henrist/greedy which is installed by default in the
Docker container.

### SSH connections

The test scripts will connect to the other servers as root,
because it modifies the network configuration when running.

It needs ssh keys so it can SSH into the root user on all machines.
You should also set up a ControlPersist for higher efficiency when
doing remote SSH commands:

Add to `/etc/ssh/ssh_config` on the AQM machine:

```
Host 10.0.0.1 10.0.0.2 10.0.0.3
    ControlMaster auto
    ControlPersist yes
    ControlPath ~/.ssh/socket-%r@%h:%p
    AddressFamily inet
```

Replace the IPs with the ones you have on the clients/servers.
This should only be for the management network!

### Defining the environment

See the template `aqmt.env.template` and drop a modified version in
`/etc/aqmt.env`. It will be read by the framework so it knows your server
setup.

### Uploading tools and configuration to client/servers

The clients and servers needs a few scripts, as well as knowledge
of the environment.

On the AQM-machine:

```bash
# on the AQM-machine
source bin/aqmt-vars.sh
aqmt-update-nodes-data
```

### Building dependencies

We need to build some C++ programs (the ones who capture traffic and
analyze the captures):

```bash
# on the AQM-machine
make
```

### Adding ARP table entries

If you want to test for stability, you don't want the tests to be interrupted
with the network stack doing ARP requests.

```bash
# on the AQM-machine
aqmt-add-arp-entries
```

See the script for details.
