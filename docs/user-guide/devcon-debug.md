# Dev Container and Debugger

The `nwm-rte` repository contains various files to support a Dev Container and VS Code debugger experience.

## Primary Files

### `.devcontainer/devcontainer.json`

`devcontainer.json` defines the Dev Container itself.

In it are choices for the image used, as well as various file mounts that occur when the Dev Container is launched.

This file also uses a `"postStartCommand"` directive to run a shell script `./.devcontainer/devcontainer.json.poststart.sh` when it starts.

### `.devcontainer/devcontainer.json.poststart.sh`

`./.devcontainer/devcontainer.json.poststart.sh` runs when the Dev Container starts. This script has commented-out `pip install` calls which can be enabled in order to cause the Dev Container to use those local codebases for some of its component packages. When those packages are pip installed with the `-e` flag, then the user can edit (the Python aspects of) those component packages and see the effects "live" while they are in the container. This also allows the user to conveniently leverage a `debugpy` debugger, since breakpoints may be placed in the component packages' code, either by adding `debugpy.breakpoint()` in-line in the Python code or by leveraging the built-in IDE breakpoint capabilities (clicking in the margins of the editor).

### `.devcontainer/launch.json`

`launch.json` defines the available VS Code debugger configurations available once inside the Dev Container. The "compounds" and "configurations" listed in this file become choosable items in the VS Code GUI's Debugger dialog, once inside the Dev Container. Review this file to see what the various configurations do. They generally run a script or a module with explicit arguments.

Do not choose configurations that begin with an underscore, as those are meant to be private (they are not functional alone, they are called on by the public configurations).

### `.devcontainer/tasks.json`

`tasks.json` contains extra code required for some of the debugger configurations. For example for the complex configurations that involve multiple concurrent MPI ranks, the debugger uses a `sleep` directive to allow the main processes some time to start up before it sends external `debugpy` instances to "attach" to those ranks.

## Steps for Building and Running the Dev Container

### Prerequisites

1. Go through the setup steps outlined in the `nwm-rte` `README.md` for cloning sibling repositories and setting up with data.

2. Build a ngen RTE image (review [`config.bashrc`](../reference/shell.md#config.bashrc) and build via `./ngen_rte_build.sh`). Be sure to choose `INSTALL_DEBUGGERS="YES"` before building, so that `debugpy` and `gdb` are installed into the RTE image. When the build finishes, note in the final terminal messages the name (tag) of the image that has been built. Commonly, it will be `"ngen_rte_ghcr"`, but not always depending on your settings.

3. Build at least one calibration realization for the test gage `"01123000"` using AORC forcing, objective function `"kge"`, and optimization algorithm `"dds"`. See the appropriate commands in either [`run_calib.sh`](../reference/shell.md#run_calib.sh) or [`run_suite.sh`](../reference/shell.md#run_suite.sh) for this. It is not necessary to fully run either of those scripts, only enough to generate intermediary output files such as `.../run_ngen/kge_dds/test_bmi/01123000/Input/forcing_config/aorc_config.yml`.

### Build and Enter the Dev Container

4. Review `.devcontainer/devcontainer.json`, especially the image name near the top. Edit as necessary.

5. Ensure your VS Code instance is at the `nwm-rte` root. Commonly, you may have your VS Code instance at the parent of this location.  If that is the case, simply run the following command to open a new VS Code instance in the `nwm-rte` repository (this will not close your existing VS Code instance): `code nwm-rte`.

6. Build and enter the Dev Container. Press key combination `ctrl-shift-P` to open the built-in Command Pallette, and start typing the word Rebuild into that dialog. You should see a choice appear named `Dev Container: Rebuild and Reopen in Container`. Choose that. This does not re-build the entire ngen RTE image. But it may take a moment for it to start a new container of your chosen (existing) image, perform the mounts, and run the `"postStartCommand"` script.

### Use the Dev Container

7. Once inside the container, you can edit `devcontainer.json` as needed and then re-build it by choosing `Dev Containers: Rebuild Container` in the Command Pallette.

8. From inside the container, if you edit code from one of the paths that was mounted to a `./src/` path (see mounts in `devcontainer.json`), note that those changes will affect your host disk since those paths are mounted.  When you rebuild using `Dev Containers: Rebuild Container`, your changes will be applied. However, if you wish to apply live changes without having to rebuild each time, you can edit `./.devcontainer/devcontainer.json.poststart.sh` as needed to enable pip (re)install calls with the `-e` flag.

9. Try running one of the simple debugger configurations, such as `forcing_nompi`.

10. Try running a complex debugger configuration, such as `forcing_mpi_n2`.

## Caveats

When running a debugger configuration, sometimes the first 1 or 2 attempts fail due to pop-up error messages such as "Configured debug type 'debugpy' is not supported.", even if you have debugpy installed. Please try a few more times and it will likely start working.

If you are trying a complex configuration that involves concurrent MPI ranks, and you are running into unexpected errors, you may need to increase the sleep time in `.devcontainer/tasks.json`, depending on your computer specifications.
