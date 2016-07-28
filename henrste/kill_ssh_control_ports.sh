#!/bin/bash

# this scripts kills the ssh tunnels that is created due to the special ssh_config setup
# (see NOTES.md)

pgrep -f "/.ssh/socket" | xargs kill
