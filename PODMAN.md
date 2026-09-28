# Podman Build and Test

**WARNING**: GitHub requires repository write access to trigger a manual workflow.

**WARNING**: Any user authorized to dispatch the [`build-and-test-podman.yml`](.github/workflows/build-and-test-podman.yml) workflow can select `push_image=true`.
When `push_image` is true, this implicitly gives `packages: write` permission to that job's `GITHUB_TOKEN`, for publishing to GHCR.
This permission applies to the job token and does not elevate the user's account permissions.


## About

This describes initial Podman compatibility testing that was performed in September 2026, and related scripts and GHA CI workflows.

Some of the workflow patterns and GitHub Actions syntax were adapted from the `ngen-forcing` repository's `podman-smoke.yml` workflow, in the `ngen-forcing` branch `feature/podman-smoke`.


## Usage

To build the RTE image with Podman and run its test, run [`./run_podman_build_and_test.sh`](run_podman_build_and_test.sh) after installing `podman`.

Note that you may wish to manually pull an updated ngen base image, as referenced by `NGEN_BASE_IMAGE`, before building the Podman image.


## Behavior

The script builds and tests a local image, after cloning sibling repositories.
It does not log in to a registry or push an image to a remote registry. If `GITHUB_TOKEN`
is set, the script passes it to the build as a secret so `add_git_info.py` can make
authenticated GitHub API requests without embedding the token in an image layer.

The script sources [config.bashrc](config.bashrc), but applies its own overrides for
`NGEN_BASE_IMAGE` and `TARGET_IMAGE_NAME`.

The [`build-and-test-podman.yml`](.github/workflows/build-and-test-podman.yml) GHA CI
workflow runs the script and optionally publishes the image to GHCR afterward.


## Publishing to GHCR

GHCR publishing is disabled by default, and is available by running a manual workflow dispatch and leveraging the `push_image` workflow variable.
When `push_image` is true, this implicitly gives `packages: write` permission to that job's `GITHUB_TOKEN`, for publishing to GHCR.
This permission applies to the job token and does not elevate the user's account permissions.

The publishing job uses the GitHub Environment `podman-ghcr-publish` defined in [`build-and-test-podman.yml`](.github/workflows/build-and-test-podman.yml).
A repository owner can configure that environment in repository settings to require reviewers, prevent
self-review, and restrict deployments to trusted branches such as `main` and `development`.
The environment name in the workflow does not provide those protections until the owner
configures its deployment protection rules.

When publishing to GHCR, it publishes only the tags `:podman-test` and `:<commit-sha>-podman-test`.
It does not modify production image tags.
