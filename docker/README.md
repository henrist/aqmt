# Internal testbed using docker

Prerequirements:
* [docker](https://docs.docker.com/engine/installation/)
* [docker-compose](https://docs.docker.com/compose/install/)

Docker uses the host kernel. As such all Docker containers will share
the same kernel.

We need to compile some things outside Docker, so some more requirements:

```bash
sudo apt install \
  g++ \
  libpcap-dev \
  make
```

You probably also need your kernel headers if you want to compile
a custom scheduler.

## A note about kernel modules and kernel configuration

We are not allowed to load/unload kernel modules inside the Docker containers,
and some parameters are not available inside Docker (such as rmem/wmem
configuration).

This means we have to build and load our custom schedulers outside Docker
before we can use them inside.

## Starting the Docker environment

See https://github.com/henrist/aqmt-example as it does all this for you,
and look in this README to understand what is going on.

If you have not set up to use Docker without root (and you are not root
on the server), prepend any `docker-compose` commands with `sudo`.

```bash
# Go to the root of aqmt repo
cd ..

# Build our programs
make all aqmt_docker

# (Build your scheduler and load them too, see example repo)

# Go in docker folder
cd docker

# Start the containers (it will be built the first time)
# Make sure to replace TEST_PATH, it should point to a directory
# that will be mounted to /opt/testbed inside Docker.
# The framework itself will be mounted at /opt/aqmt.
TEST_PATH=/your/path/containing/test/scripts docker-compose up -d

# when your are back in the terminal, connect to the aqm machine
./ssh.sh aqm

# Run your tests you have mounted in by TEST_PATH
# You should run everything inside tmux session (inside Docker) in case
# you loose connection or want to detach and attach again later.
```

If you are unfamiliar with tmux, see
[tmuxcheatsheet.com](https://tmuxcheatsheet.com/)

## Patching iproute2

You might need a patched iproute2 if you have changed the API of any
schedulers or added new schedulers.

You can drop any patch files inside `container/iproute2-patches` and they
will be applied when building the Docker image.

NOTE: If you keep this patchfile stored in a repository, you can't symlink
it to this directory. You will have to _copy_ it when you change it.

See Dockerfile for which branch is used to patch on top of iproute2.

```bash
# add iproute2 if you don't have it already
cd my-custom-iproute2
git remote add iproute2 git://git.kernel.org/pub/scm/linux/kernel/git/shemminger/iproute2.git
git fetch iproute2

# make a diff
cd iproute2-l4s
git diff v4.10.0 >/path/to/docker/container/iproute2-patches/my-file.patch
```

The patch files must end with `.patch`.

To rebuild the Docker-image so your patch is included, run:

```bash
docker-compose build
```

Remember to start the containers again so they will use the new build.
