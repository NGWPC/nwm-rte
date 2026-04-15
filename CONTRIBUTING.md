# Guidance on how to contribute

> All contributions to this project will be released to the public domain.
> By submitting a pull request or filing a bug, issue, or
> feature request, you are agreeing to comply with this waiver of copyright interest.
> Details can be found in our [TERMS](TERMS.md) and [LICENSE](LICENSE.md).


There are two primary ways to help:
 - Using the issue tracker, and
 - Changing the code-base.


## Using the issue tracker

Use the issue tracker to suggest feature requests, report bugs, and ask questions.
This is also a great way to connect with the developers of the project as well
as others who are interested in this solution.

Use the issue tracker to find ways to contribute. Find a bug or a feature, mention in
the issue that you will take on that effort, then follow the _Changing the code-base_
guidance below.


## Changing the code-base

Generally speaking, you should fork this repository, make changes in your
own fork, and then submit a pull request. All new code should have associated
unit tests that validate implemented features and the presence or lack of defects.
Additionally, the code should follow any stylistic and architectural guidelines
prescribed by the project. In the absence of such guidelines, mimic the styles
and patterns in the existing code-base.

### Code Formatting and Linting

#### Python Code

For auto-formatting Python code, please use `black` with default line length (88), or equivalent such as `Ruff`.

For linting, please follow PEP 8 guidelines, using `Ruff` or equivalent.

Please include type hints and docstrings on all classes, methods, and functions.  For docstring formatting, please follow the `numpy` style.  `MkDocs` has been configured to parse this style via the `mkdocstrings` package.


#### Shell Code

Please follow the `shellman` style for in-file documentation. `MkDocs` has been configured to parse this style of docstring via the `mkdocstrings-shell` package.


## Updating the Documentation

To update the documentation, run the following commands from the `nwm-rte` repository root.

```shell
# Install dependencies needed to build the documentation.
pip install ".[docs]"

# Update the Python CLI --help txt files, if necessary. Commit txt file changes to the repository as needed.
./docs/update_python_cli_ref.sh

# Serve the documentation locally and confirm changes in the browser at http://127.0.0.1:8000/nwm-rte/
mkdocs serve

# Make git commits and pushes as needed.
...

# Deploy to the GitHub pages site
mkdocs gh-deploy
```
