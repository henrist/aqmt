export IP_AQM_MGMT=10.25.0.2
export IP_AQM_C=10.25.1.2
export IP_AQM_SA=10.25.2.2
export IP_AQM_SB=10.25.3.2

export IP_CLIENTA_MGMT=10.25.0.11
export IP_CLIENTA=10.25.1.11

export IP_CLIENTB_MGMT=10.25.0.12
export IP_CLIENTB=10.25.1.12

export IP_SERVERA_MGMT=10.25.0.21
export IP_SERVERA=10.25.2.21

export IP_SERVERB_MGMT=10.25.0.31
export IP_SERVERB=10.25.3.31

# entrypoint.sh generates testbed-vars-local.sh
if [ -f /tmp/testbed-vars-local.sh ]; then
    . /tmp/testbed-vars-local.sh
fi
