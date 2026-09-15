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

if [ "$install_debuggers" = "YES" ]; then
    echo "Installing debugpy via pip"
    pip install debugpy
    echo "Installing gdb"

    . /etc/os-release
    if [ "$ID" = "rocky" ]; then
        dnf install -y gdb
        yum install yum-utils -y
        yum-config-manager --enable baseos-debug

        # Rocky 8's python3 is platform-python/a modular stream, neither of which has published debuginfo
        if [ "${VERSION_ID%%.*}" -ge 9 ]; then
            echo "Rocky $VERSION_ID detected. Installing gdb and Python debug symbols"
            debuginfo-install -y python3
        else
            echo "Rocky $VERSION_ID detected. Installing gdb. Python debug symbols are not published for this release and will not be installed."
        fi
    elif [ "$ID" = "debian" ]; then
        echo "Debian detected. Installing gdb. Python debug symbols will not be installed."
        apt-get update
        apt-get install -y gdb libc6-dbg
    else
        echo "Error: unexpected OS: ID=$ID"
        exit 1
    fi

elif [ "$install_debuggers" = "NO" ]; then
    echo "Not installing debuggers"

else
    echo "ERROR: invalid CLI value for install_debuggers (expected YES or NO): ${install_debuggers}"
    exit 1
fi
