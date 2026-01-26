#!/bin/bash

set -euo pipefail

install_debuggers=$1

if [ "$install_debuggers" = "YES" ]; then
    echo "Installing debugpy via pip"
    pip install debugpy
    echo "Installing gdb via dnf"
    dnf install -y gdb

elif [ "$install_debuggers" = "NO" ]; then
    echo "Not installing debuggers"

else
    echo "ERROR: invalid CLI value for install_debuggers (expected YES or NO): ${install_debuggers}"
    exit 1
fi
