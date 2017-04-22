all: keys docker_build

clean: remove_keys


keys:
	# These keys are volume mounted into the container so that we can easily
	# ssh into the container. Note that even tho it is not recommended to run
	# a ssh daemon inside Docker, this is basicly the "service" we expose
	# between the different containers, so it isn't really wrong.
	test -f container/id_rsa || ssh-keygen -t rsa -b 4096 -C docker-testbed -f container/id_rsa -N ''

docker_build:
	docker-compose build


remove_keys:
	rm -rf container/id_rsa container/id_rsa.pub

clear_known_hosts:
	ssh-keygen -f "/home/${USER}/.ssh/known_hosts" -R 10.25.0.2
	ssh-keygen -f "/home/${USER}/.ssh/known_hosts" -R 10.25.0.11
	ssh-keygen -f "/home/${USER}/.ssh/known_hosts" -R 10.25.0.12
	ssh-keygen -f "/home/${USER}/.ssh/known_hosts" -R 10.25.0.21
	ssh-keygen -f "/home/${USER}/.ssh/known_hosts" -R 10.25.0.22
