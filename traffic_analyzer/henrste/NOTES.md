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
