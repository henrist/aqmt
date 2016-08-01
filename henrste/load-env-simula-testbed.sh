# Simula testbed setup

# interfaces:
#   enp2s0f1   To client A (10.0.1.211) and client B (10.0.1.210)
#   enp2s0f2   To server A (10.0.3.201)
#   enp2s0f3   To server B (10.0.2.200)

export IFACE_CLIENTS=enp2s0f1
export IFACE_SERVERA=enp2s0f3
export IFACE_SERVERB=enp2s0f2

export IP_AQM_MGMT=192.168.200.211
export IP_AQM_C=10.0.1.100
export IP_AQM_SA=10.0.3.100
export IP_AQM_SB=10.0.2.100

export IP_CLIENTA_MGMT=192.168.202.10
export IP_CLIENTA=10.0.1.211

export IP_CLIENTB_MGMT=192.168.200.206
export IP_CLIENTB=10.0.1.210

export IP_SERVERA_MGMT=172.16.0.127
export IP_SERVERA=10.0.3.201

export IP_SERVERB_MGMT=192.168.200.203
export IP_SERVERB=10.0.2.200

export IFACE_ON_SERVERA=enp3s0
export IFACE_ON_SERVERB=enp3s0
# TODO: clients?
