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
|  |- 📂 tests
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
* `bin/tests` contains unit tests for the utility modules in `bin`. These are
  not tests for any of the Harmony services.
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

## What happens during a workflow run?

Every night, [a workflow](https://github.com/nasa/harmony-autotester/blob/main/.github/workflows/test_all_associated_collections.yaml)
is executed. This workflow:

* Queries CMR GraphQL to discover all  services with a type of "harmony".
  Basic service information is retrieved, along with key fields for every
  collection associated with each service.
* If an entry exists mapping the service to a directory in this repository,
  `pytest` is executed on a test suite in the identified directory.
* The following behaviour is then followed:
  * If a collection failed a test, and there is no existing open GitHub issue
    for that combination of collection and service, a new GitHub issue is made.
  * If a collection failed a test, and there is already an open GitHub issue
    for that combination of collection and service, the existing GitHub issue
    is updated to state the most recent failure date.
  * If a collection and service combination has an open GitHub issue, but the
    tests passed, then that GitHub issue is updated to indicate the date the
    tests passed.
  * If a collection and service combination has an open GitHub issue, but the
    collection is no longer associated with the service, the GitHub issue is
    updated to indicate a lack of association.

The above functionality relies on GitHub labels on open issues in the
repository. These use human-readable fields in the collection and service
metadata. While these are much more user-friendly, these fields are mutable,
and so will result in new issues being created if the collection short name,
collection version or service name are updated in CMR.

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

### Common test fixtures:

`tests/conftest.py` contains test fixtures, classes and functions that should
be reused between different test suites. These include:

* `AutotesterRequest` - A child class of the `harmony-py` `Request` class that
  has the same functionality, but adds a label to the job: 'harmony-autotester'.
* `harmony_client` - Authenticated client using EDL credentials and environment
  as defined via environment variables for the test workflow.
* `service_collection` - A parametrised test fixture that allows a test that is
  executed to iterate through all collections associated with a service. These
  collections are supplied by a JSON blob saved to an environment variable.
* `failed_tests` - An aggregating list that should gain entries for every
  failed test. The contents of this fixture get written out to the
  `test_output.json` file saved to the directory for the test suite.

### Requirements for test failure elements:

Each entry in the `failed_test` list should be structured as follows:

```
{
  "short_name": "<short name of the collection>",
  "version": "<version of the collection>",
  "concept_id": "<concept ID of the collection>",
  "error": "String representation of failure",
  "url": "Harmony request URL for failed request, allowing for reproduction"
}
```

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

The Harmony Autotester does not produce published artefacts capturing changes
to the tset suites, as the repository itself _is_ the artefact. However, it is
useful to denote when large pieces of functionality are added or updated to
the overall autotester, such as changing the core CI/CD or adding/updating
individual test suites.

Version information is captured by two files:

* `version.txt`
* `CHANGELOG.md`

`version.txt` contains a semantic version number. When this file is updated a
GitHub workflow will be triggered that creates a new GitHub release.

The `CHANGELOG.md` file requires a specific format for a new release, as it
looks for the following string to define the newest release of the autotester
(starting at the top of the file).

```
## [vX.Y.Z] - YYYY-MM-DD
```

Additionally, the markdown reference from this release subtitle needs to be
added to the bottom of the file following the existing pattern.

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
