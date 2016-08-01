FROM ubuntu:xenial
MAINTAINER Henrik Steen <henrist@henrist.net>

# set up custom iproute2
# (patch is originally written for branch v3.16.0 of iproute2,
#  using v4.6.0 for support of 'ip route congctl')
ADD container/iproute2.patch /opt/
WORKDIR /opt
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
         bison \
         build-essential \
         flex \
         git \
         iptables-dev \
         libdb5.3-dev \
         patch \
         pkg-config \
    && rm -rf /var/lib/apt/lists/* \
    && git clone --depth=1 --branch=v4.6.0 git://git.kernel.org/pub/scm/linux/kernel/git/shemminger/iproute2.git iproute2 \
    && cd iproute2 \
    && patch -p1 <../iproute2.patch \
    && make \
    && make install \
    && rm -rf /opt/iproute2 \
    && apt-get remove -y bison build-essential flex git iptables-dev libdb5.3-dev patch pkg-config \
    && apt-get autoremove -y

# set up ssh and custom packages
ADD container/id_rsa /root/.ssh/
ADD container/id_rsa.pub /root/.ssh/
ADD container/id_rsa.pub /root/.ssh/authorized_keys
RUN chmod 600 /root/.ssh/* \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
         bc \
         ca-certificates \
         git \
         iputils-ping \
         netcat-openbsd \
         iperf3 \
         iptraf \
         less \
         net-tools \
         openssh-server \
         psmisc \
         speedometer \
         sudo \
         tcpdump \
         tmux \
         vim \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir /var/run/sshd \
    \
    # dont check host keys when connecting
    && sed -i 's/#   StrictHostKeyChecking .*/    StrictHostKeyChecking no/' /etc/ssh/ssh_config \
    \
    # SSH login fix. Otherwise user is kicked off after login
    && sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd \
    \
    && echo ". /tmp/testbed-vars.sh" >>/etc/bash.bashrc \
    && echo ". /tmp/testbed-vars.sh" >>/etc/profile.d/testbed.sh

ADD container/entrypoint.sh /entrypoint.sh

EXPOSE 22
ENTRYPOINT ["/entrypoint.sh"]
CMD ["/usr/sbin/sshd", "-D"]
