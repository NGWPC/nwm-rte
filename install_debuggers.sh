#!/bin/bash

set -euo pipefail

## 
## \brief
## Install debugger packages. Used by `Dockerfile.rte`.
## 
## \desc
## Install debugger packages: python package `debugpy` and OS package `gdb`. Used by `Dockerfile.rte`.
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
python_version=${2:-}

if [ "$install_debuggers" = "YES" ]; then
    echo "Installing debugpy via pip"
    pip install debugpy
    echo "Installing gdb"

    if grep -q '^ID=rocky' /etc/os-release; then
        echo "Rocky detected. Installing gdb and Python debug symbols"
        dnf install -y gdb
        yum install yum-utils -y
        yum-config-manager --enable baseos-debug
        debuginfo-install python${python_version}
    elif grep -q '^ID=debian' /etc/os-release; then
        echo "Debian detected. Installing gdb. Python debug symbols will not be installed."
        apt-get update
        apt-get install -y gdb libc6-dbg
    else
        echo "Error: unexpected OS: `grep ^ID /etc/os-release`"
        exit 1
    fi

elif [ "$install_debuggers" = "NO" ]; then
    echo "Not installing debuggers"

else
    echo "ERROR: invalid CLI value for install_debuggers (expected YES or NO): ${install_debuggers}"
    exit 1
fi
