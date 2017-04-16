keys:
	test -f container/id_rsa || ssh-keygen -t rsa -b 4096 -C docker-testbed -f container/id_rsa -N ''
clean:
	rm -rf container/id_rsa container/id_rsa.pub
clear_known_hosts:
	ssh-keygen -f "/home/${USER}/.ssh/known_hosts" -R 10.25.0.2
	ssh-keygen -f "/home/${USER}/.ssh/known_hosts" -R 10.25.0.11
	ssh-keygen -f "/home/${USER}/.ssh/known_hosts" -R 10.25.0.12
	ssh-keygen -f "/home/${USER}/.ssh/known_hosts" -R 10.25.0.21
	ssh-keygen -f "/home/${USER}/.ssh/known_hosts" -R 10.25.0.22
