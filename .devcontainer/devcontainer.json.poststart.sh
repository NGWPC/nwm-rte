#!/bin/bash

set -euo pipefail
set -x

### Reinstall a specific ngen extern submodule
# python -m pip install -e ./src/ngen/extern/lstm

### Reinstall forcing (Python package only)
# python -m pip install -e ./src/ngen-forcing

### Reinstall various components
# python -m pip install -e ./src/nwm-fcst-mgr
# python -m pip install -e ./src/nwm-msw-mgr
# python -m pip install -e ./src/nwm-cal-mgr

exit 0
