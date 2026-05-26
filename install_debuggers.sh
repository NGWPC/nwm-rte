#!/bin/bash

set -euo pipefail

## 
## \brief
## Install debugger packages. Used by `Dockerfile.rte`.
## 
## \desc
## Install debugger packages: python package `debugpy` and dnf package `gdb`. Used by `Dockerfile.rte`.
## Optionally skip installation (noop). The choice of noop is to abstract the flow control away into
## a parameter to work around the non-branching nature of Docker build flow control.
## 
## Has 1 positional argument and 0 named arguments.
## 
## \option install_debuggers
## Choose from: `["YES", "NO"]`. If `"NO"`, this is a noop.
## 
## \usage ./install_debuggers.sh YES
## \usage ./install_debuggers.sh NO
## 

install_debuggers=$1

if [ "$install_debuggers" = "YES" ]; then
    echo "Installing debugpy via pip"
    pip install debugpy
    echo "Installing gdb via dnf"
    dnf install -y gdb
    yum install yum-utils -y
    yum-config-manager --enable baseos-debug
    # TODO parameterize or auto-determine Python version
    debuginfo-install python3.11

elif [ "$install_debuggers" = "NO" ]; then
    echo "Not installing debuggers"

else
    echo "ERROR: invalid CLI value for install_debuggers (expected YES or NO): ${install_debuggers}"
    exit 1
fi
