# Custom Builds

## Example for a Custom Build of `ngen`

Here are steps for making the RTE image using a custom version of `ngen` itself. These steps assume that the default version of `ngen-forcing` (referenced by `ngen/Dockerfile`) is the desired base, prior to adding the `ngen` layer.

1. Run the above setup steps for cloning repos and downloading data, except stop before running `./ngen_rte_build.sh`.

2. Edit [`config.bashrc`](../reference/shell.md#config.bashrc) to use: `NGEN_SOURCE_MODE="build_from_local"`

3. Check out the desired code for ngen and its submodules.  For example, to use `ngen`'s `development` branch but change the version of `t-route`:
```shell
### From the ~/ngwpc/ngen repository root:
git checkout development
git pull
## Ensure the local copies of submodules are matching the specific commits currently pointed to by the ngen repository.
## This does not fetch the latest updates from the submodule branches tracked by .gitmodules.  To do that, you would add --remote to the command.
git submodule update --init --recursive
## Check out a specific branch of t-route
( cd extern/t-route && git checkout any-branch && git pull )
```

4. If your `ngen/Dockerfile` is starting `FROM ghcr.io/ngwpc/ngen-bmi-forcing:latest`, then pull the latest ngen-forcing GHCR image.
```shell
sudo docker pull ghcr.io/ngwpc/ngen-bmi-forcing:latest
```

5. Build the RTE image
```shell
### From the ~/ngwpc/nwm-rte repository root:
./ngen_rte_build.sh
```

6. Confirm in the build messages that the built was successful and that the image name built is `ngen_rte_build_from_local`

## See Also

For (re)installing the Python packages of ngen's submodules, such as `lstm`, within the Dev Container, see [.devcontainer/devcontainer.json.poststart.sh](devcon-debug.md#devcontainerdevcontainerjsonpoststartsh)
