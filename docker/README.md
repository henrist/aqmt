# Internal testbed using docker

Prerequirements:
* docker
* docker-compose

## Starting the services

`docker-compose up`

This will bring up all the containers and network configuration

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
