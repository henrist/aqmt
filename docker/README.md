# Internal testbed using docker

Prerequirements:
* docker
* docker-compose

## Starting the services

`docker-compose up -d --build`

This will bring up all the containers and network configuration.

## Loading kernel modules (the schedulers)

We do not allow kernel modules to be loaded inside the Docker containers,
so they have to be compiled and loaded on the host before trying to use
them inside the container.

```bash
# on host os, not inside Docker
cd sch_pi2
make
sudo make load
```

Now the scheduler can be used inside a Docker container.

## Generating patch for iproute2

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
