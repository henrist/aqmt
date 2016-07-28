## Useful utils

`bmon`


## Nice overview of Traffic Control in Linux

http://wiki.linuxwall.info/doku.php/en%3aressources%3adossiers%3anetworking%3atraffic_control


## Simple static speed test

server (e.g. on `server-a`):  
`while true; do nc -l 1234 >/dev/null; done`

client:  
`sudo dd if=/dev/zero bs=1024k | nc server-a 1234`

It will push data to server until it is ended


## Speed up SSH-commands

Add to `/etc/ssh/ssh_config`:

```
Host 10.* server-* client-*
    ControlMaster auto
    ControlPersist yes
    ControlPath ~/.ssh/socket-%r@%h:%p
    AddressFamily inet
```


## Investigate socket status

`ss -nei '( sport >= 1234 and sport <= 1240 )'`


## Running iperf3

Server side:  
`iperf3 -s`

Client side:  
`iperf3 -c server-a -R -w 1M -N`


## Usefull tcpdump commands

See:

https://www.wains.be/pub/networking/tcpdump_advanced_filters.txt

https://danielmiessler.com/study/tcpdump/


## Show rate in tc class info details for htb classes

Need to run the following to activate it, and then reload the htb tables

`echo 1 > /sys/module/sch_htb/parameters/htb_rate_est`

### Tools

#### Wireshark 2.0 on Ubuntu

See http://ubuntuhandbook.org/index.php/2015/11/install-wireshark-2-0-in-ubuntu-15-10-wily/

(`sudo add-apt-repository ppa:wireshark-dev/stable`)

## Oneliners

```bash
sudo ip tuntap add dev tap0 mode tap
sudo ip addr add 10.0.3.202 dev tap0
sudo ip link set tap0 up
brctl addbr br0
ip link set br0 up
brctl addif br0 tap0
brctl addif br0 enp3s0
ip a del 10.0.3.201/24 dev enp3s0
ip a add 10.0.3.201/24 dev br0
route add -net 10.0.1.0 gw 10.0.3.100 netmask 255.255.255.0 dev br0
ping -I tap0 10.0.1.100
sudo tcpdump -v -i enp3s0 '(src 10.0.1.211 or dst 10.0.1.211)'
# server-a: 172.16.0.127/22
```
