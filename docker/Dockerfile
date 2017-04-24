FROM ubuntu:xenial
MAINTAINER Henrik Steen <henrist@henrist.net>

# set up ssh and custom packages
ADD container/speedometer.patch /opt/
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
         bc \
         ca-certificates \
         dstat \
         ethtool \
         git \
         gnuplot \
         inotify-tools \
         iputils-ping \
         iperf \
         iperf3 \
         iptraf \
         ipython3 \
         less \
         net-tools \
         netcat-openbsd \
         nmap \
         openssh-server \
         patch \
         psmisc \
         python \
         python-urwid \
         python3-numpy \
         python3-plumbum \
         sudo \
         tcpdump \
         tmux \
         vim \
         wget \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir /var/run/sshd \
    \
    && wget -O /usr/bin/speedometer https://raw.githubusercontent.com/wardi/speedometer/9211116e8df11fc6458489b209de2900ab2e3e84/speedometer.py \
    && (cd /usr/bin; patch </opt/speedometer.patch) \
    && chmod +x /usr/bin/speedometer \
    \
    # dont check host keys when connecting
    && sed -i 's/#   StrictHostKeyChecking .*/    StrictHostKeyChecking no/' /etc/ssh/ssh_config \
    \
    # SSH login fix. Otherwise user is kicked off after login
    && sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd \
    \
    # optimize ssh connection by persisting connection
    && echo "Host 10.25.0.*" >>/etc/ssh/ssh_config \
    && echo "    ControlMaster auto" >>/etc/ssh/ssh_config \
    && echo "    ControlPersist yes" >>/etc/ssh/ssh_config \
    && echo "    ControlPath ~/.ssh/socket-%r@%h:%p" >>/etc/ssh/ssh_config \
    && echo "    AddressFamily inet" >>/etc/ssh/ssh_config \
    \
    && echo ". /aqmt-vars.sh" >>/etc/bash.bashrc \
    && echo "cd /opt/testbed" >>/etc/bash.bashrc \
    && echo ". /aqmt-vars.sh" >>/etc/profile.d/aqmt.sh \
    && echo 'PATH="/opt/aqmt/bin:$PATH"' >>/etc/bash.bashrc \
    && echo 'export PYTHONPATH="/opt/aqmt:$PYTHONPATH"' >>/etc/bash.bashrc

COPY container/iproute2-patches /opt/iproute2-patches
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
    \
    # set up custom iproute2 (we need at least v4.6.0 for 'ip route congctl' support
    && cd /opt \
    && git clone --depth=1 --branch=v4.10.0 git://git.kernel.org/pub/scm/linux/kernel/git/shemminger/iproute2.git iproute2 \
    && cd iproute2 \
    && find /opt/iproute2-patches -name "*.patch" -print0 | sort -z | \
         xargs --no-run-if-empty -0 -l patch -p1 -f --fuzz=3 -i \
    && make \
    && make install \
    && cd /opt \
    && rm -rf /opt/iproute2 \
    \
    # set up greedy
    && wget -O /usr/bin/greedy https://github.com/henrist/greedy/releases/download/v0.1/greedy \
    && chmod +x /usr/bin/greedy \
    \
    && apt-get remove -y bison build-essential flex git iptables-dev libdb5.3-dev patch pkg-config \
    && apt-get autoremove -y

# create a file that can be used to identify we are in Docker
RUN touch /.dockerenv

ADD container/entrypoint.sh /entrypoint.sh

EXPOSE 22
ENTRYPOINT ["/entrypoint.sh"]
CMD ["/usr/sbin/sshd", "-D"]
