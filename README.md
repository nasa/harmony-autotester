# Harmony Autotester

This repository contains and executes testing for Harmony backend services. The
scope of these tests is to be a rough sanity check that all collections
associated with a Harmony service chain can be processed by that chain. The
tests are not extensive, nor are they scientifically rigorous. They should
establish that a collection can be processed by a service chain without errors
or obviously incorrect output.

## What the Harmony Autotester does:

The Harmony Autotester provides simple, non-rigorous testing of all NASA
Earth Science collections supported by the [Harmony](https://harmony.earthdata.nasa.gov)
workflow manager.

All Harmony services are identified using the Common Metadata Repository (CMR),
and all collections associated with those services are also retrieved. For each
service, a set of basic tests are executed for all associated services,
primarily ensuring the request succeeds.

If a test fails for a collection/service pairing, a GitHub issue will be created
in the repository, to allow for tracking of any related issues.

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

## Adding a new test suite:

Each service chain should have a dedicated subdirectory in the `tests` directory.
Within that subdirectory, at a minimum, should be:

* `tests_<service_name>.py` - A `pytest` compatible file with tests that will
  be run for all associated collections.
* `requrements.txt` - A file with requirements that can be installed via Pip.
* `__init__.py` - This will ensure that the tests within the directory are
  discoverable by `pytest`.

Other files could be added as needed, including items such as utility
functions. However, it is recommended to keep the tests as small in scope
as possible. These tests should be a lightweight, sanity check that the
service and collection pairing is valid, not a rigorous confirmation of the
validity of the output. Bear in mind that tests will have to be run against
_every_ collection the service is associated with.

For an example test directory, see `tests/hybig`:

* `tests/hybig/requirements.txt` - Python packages needed for the test suite.
* `tests/hybig/test_hybig.py` - A single test and supporting utility function.
  This test will be run against every collection associated with that service.

Once a test directory has been created, the GitHub workflow that runs every
night will need to be aware of it. To enable the tests, update the mappings in
`bin/production_service_mapping.json` and/or `bin/uat_service_mapping.json` to
include the UMM-S concept ID and the name of the new test directory. The UMM-S
concept ID is used as it is immutable. It is possible to also configure tests
only for either UAT or production by only including information for the test
directory in the appropriate mapping.

### Managing dependencies:

There is a file containing the common dependencies that all test suites will
use, `tests/common_requirements.txt`. Each `tests/<service>/requirements.txt`
should include those dependencies by using the following line:

```
-r ../common_requirements.txt
```

## CI/CD workflows:

These are found in the `.github/workflows` directory:

- `test_all_associated_collections.yaml` contains the main workflow for the
  Harmony Autotester, which is triggered on a nightly schedule. This workflow
  uses CMR to identify all Harmony services and their associated collections,
  before triggering the appropriate test suite to run for all collections
  associated with a particular service.

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
