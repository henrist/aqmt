# Internal testbed using docker

Prerequirements:
* [docker](https://docs.docker.com/engine/installation/)
* [docker-compose](https://docs.docker.com/compose/install/)

## Quickstart

In project root directory, build and load the schedulers:

`./load_sch.sh`

We do not allow kernel modules to be loaded inside the Docker containers,
so they have to be compiled and loaded on the host before trying to use
them inside the container.

Go into docker folder and build the Docker images:

`cd docker; docker-compose build`

Run the docker containers:

`docker-compose up -d`

Connect to the aqm node:

`./ssh.sh aqm`

Start a tmux session ([learn more about tmux](https://tmuxcheatsheet.com/)):

`tmux`

Run a test (modify `example.py` as desired):

```
cd henrste`
TEST_INTERACTIVE=1 ./example.py
```

When test is complete, look in `henrste/results` for graphs.

You can switch to the next tmux window by pressing `Ctrl+b` + `n` to see
the output from the traffic generator.

You can cancel the test by pressing `Ctrl+c`.

## Using without Docker

See the readme in `../henrste/`.

When using Docker the environment configuration is automatically sourced.
This have to be done manually by typing `. vars.sh` when not using Docker.

## Increasing the rmem and wmem tcp sizes

From project root (outside Docker):

`./henrste/utils/set_sysctl_tcp_mem.sh 5000`

To allow a TCP window up to approx. 5000 packets.

## Generating patch for iproute2

When changing the iproute2 implementation, a new patchfile have to be
built which is applied when building the Docker image we use when running
using Docker.

See Dockerfile for which branch is used to patch on top of iproute2.

You might need to have tags and branches from the main upstream
repository of iproute2, e.g. by doing:

```
cd iproute2-l4s
git remote add iproute2 git://git.kernel.org/pub/scm/linux/kernel/git/shemminger/iproute2.git
git fetch iproute2
```

Generate patch-file in iproute2-l4s-repository:

```
cd iproute2-l4s
git diff v4.6.0 >../docker/container/iproute2.patch
```
