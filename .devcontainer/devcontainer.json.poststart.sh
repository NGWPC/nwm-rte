#!/bin/bash

set -euo pipefail
set -x

### Reinstall a specific ngen extern submodule
# python -m pip install -e ./src/ngen/extern/lstm
# python -m pip install -e ./src/ngen/extern/t-route
# python -m pip install -e ./src/ngen/extern/topoflow-glacier

### Reinstall forcing (Python package only).
### If doing this with -e, also need the symlink below since -e uninstalls package data and does not reinstall it.
# python -m pip install -e ./src/ngen-forcing
# ln -s $(pwd)/src/ngen-forcing/NextGen_Forcings_Engine_BMI $(python -c "import site; print(site.getsitepackages()[0])")/NextGen_Forcings_Engine_BMI

### Reinstall nwm-ewts (Python package only)
# python -m pip install -e ./src/nwm-ewts/runtime/python/ewts

### Reinstall nwm-ewts (Python package only)
# python -m pip install -e ./src/nwm-ewts/runtime/python/ewts

### Reinstall various components
# python -m pip install -e ./src/nwm-fcst-mgr
# python -m pip install -e ./src/nwm-msw-mgr
# python -m pip install -e ./src/nwm-cal-mgr

exit 0
