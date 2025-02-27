# Harmony Autotester

This repository contains and executes testing for Harmony backend services. The
scope of these tests is to be a rough sanity check that all collections
associated with a Harmony service chain can be processed by that chain. The
tests are not extensive, nor are they scientifically rigorous. They should
establish that a collection can be processed by a service chain without errors
or obviously incorrect output.

## What the Harmony Autotester does:

TODO

## Repository Structure:

```
|- 📂 .github
|- 📂 bin
|- 📂 tests
|- .pre-commit-config.yaml
|- .snyk
|- CHANGELOG.md
|- CONTRIBUTING.md
|- LICENSE
|- README.md
|- dev_requirements.txt
|- pyproject.toml
```

* `.github` contains CI/CD workflows to be executed within the repository. For
  more information see [GitHub's documentation](https://github.com/features/actions).
* `bin` contains utility scripts for the repository.
* `tests` contains subdirectories for each Harmony backend service chain, each
  with a definition of a test to run for every collection associated with that
  service chain.
* `.pre-commit-config.yaml` contains a set of hooks to be run when developers
  commit work. These checks will ensure various coding standards are adhered to
  and will also be run as a blocking check for pull requests. For more
  information, see the pre-commit section in this README.
* `.snyk` contains information for Snyk to select the correct version of Python
  when building the dependency tree used during vulnerability scanning.
* `CHANGELOG.md` contains release notes for each version of the Harmony
  Autotester.
* `CONTRIBUTING.md` contains guidance for contributing to this project.
* `LICENSE` is the license file for this work, as defined by the NASA Open
  Source approval process.
* `README.md` is this file.
* `dev_requirements.txt` contains Pip-installable Python packages that are
  required for local development. For example, `pre-commit`.
* `pyproject.toml`  is a configuration file used by packaging tools, and other
  tools such as linters and type checkers.

## CI/CD workflows:

TODO

## Releasing:

TODO

The `CHANGELOG.md` file requires a specific format for a new release, as it
looks for the following string to define the newest release of the autotester
(starting at the top of the file).

```
## [vX.Y.Z] - YYYY-MM-DD
```

Where the markdown reference needs to be updated at the bottom of the file
following the existing pattern.

```
[unreleased]: https://github.com/nasa/harmony-autotester/
[vX.Y.Z]: https://github.com/nasa/harmony-autotester/releases/tag/X.Y.Z
```

## Versioning:

This project adheres to semantic version numbers: `major.minor.patch`.

* Major increments: These are non-backwards compatible API changes.
* Minor increments: These are backwards compatible API changes.
* Patch increments: These updates do not affect the API to the autotester.

## pre-commit hooks:

This repository uses [pre-commit](https://pre-commit.com/) to enable pre-commit
checking the repository for some coding standard best practices. These include:

* Removing trailing whitespaces.
* Removing blank lines at the end of a file.
* JSON files have valid formats.
* [ruff](https://github.com/astral-sh/ruff) Python linting checks.
* [black](https://black.readthedocs.io/en/stable/index.html) Python code
  formatting checks.

To enable these checks locally:

```bash
# Install pre-commit Python package as part of test requirements:
pip install -r dev_requirements.txt

# Install the git hook scripts:
pre-commit install

# (Optional) Run against all files:
pre-commit run --all-files
```

When you try to make a new commit locally, `pre-commit` will automatically run.
If any of the hooks detect non-compliance (e.g., trailing whitespace), that
hook will state it failed, and also try to fix the issue. You will need to
review and `git add` the changes before you can make a commit.

It is planned to implement additional hooks, possibly including tools such as
`mypy`.

[pre-commit.ci](pre-commit.ci) is configured such that these same hooks will be
automatically run for every pull request.

## Get in touch:

You can reach out to the maintainers of this repository via email:

* owen.m.littlejohns@nasa.gov
