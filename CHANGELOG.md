# Changelog

The Harmony Autotester follows semantic versioning. All notable changes to this
project will be documented in this file. The format is based on [Keep a
Changelog](http://keepachangelog.com/en/1.0.0/).

## [v1.5.1] - 2026-10-06

### Changed:

- Switched smap-l2-gridder tests to use `concept_id` when grabbing granules for
  the test.

### Fixed:

- Updated `umm_g_utilities.py` `get_bounding_box` to fail in a way that is
  captured by the test output when the granule has no spatial information
  associated with it.

## [v1.5.0] - 2026-10-01

### Added:

- DAS-2514 - Adds tests for the `sds/HOSS-geographic` service chain in
  production and UAT. For each associated collection, a granule is requested
  with a variable and bounding box subset and checks the request is successful.

### Changed:

- DAS-2514 - `get_configured_variable_names` returns `['all']` for collections with no
  configured variables.

## [v1.4.0] - 2026-09-29

### Changed:

- The Autotest CI/CD has been updated to use the `pytest-xdist` plugin and
  parallelise test execution. The number of workers will default to the
  available CPUs on the GitHub test runner executing the tests. This should
  significantly improve runtime, which already takes several hours for some of
  the few service chains configured in the Autotester.

## [v1.3.0] - 2026-09-23

### Added:

- DAS-2519 - Added `bin/get_service_collections.py`, a local development helper
  that prints every collection associated with a test directory's service in
  the format expected by the `SERVICE_COLLECTIONS` environment variable.
  Parametrised test IDs now include the collection short name, version and
  concept ID, and `TEST_DIRECTORY` defaults to the directory of the tests
  being run.

### Fixed:

- Fixes incorrect access in net2cog test to the filename from the Harmony result JSON
  by requesting the correct key from the result dictionary.

### Changed:

- Replaced manual batchee grouping with corresponding function from batchee library

- Release notes published in GitHub releases will now include a list of commit
  messages since the last release.

## [v1.2.1] - 2025-06-04

### Changed:

- TRT-570 - Updated URL to create new comments on a GitHub issue.

## [v1.2.0] - 2025-05-29

### Added:

- TRT-570 - Added tests for the [net2cog service](https://github.com/podaac/net2cog).
  These tests will ensure a request returns a successful status for a collection,
  and then check that all output files have the expected suffix on their output
  names: `_reformatted.tif`.

## [v1.1.0] - 2025-05-01

### Changed:

- TRT-619 - Main workflow made to be reusable with a `workflow_call` trigger.

### Added:

- TRT-619 - Added UAT invocation of reusable workflow.

## [v1.0.0] - 2025-04-24

### Added:

- TRT-627 - Implemented workflow to retrieve all Harmony services from CMR GraphQL
  along with all associated collections.
- TRT-630 - Implemented test suite for HyBIG.
- TRT-628 - Implemented scaffolding to invoke all defined test suites.
- TRT-629 - Implemented GitHub issue publication for failures.

[v1.5.1]: https://github.com/nasa/harmony-autotester/releases/tag/1.5.1
[v1.5.0]: https://github.com/nasa/harmony-autotester/releases/tag/1.5.0
[v1.4.0]: https://github.com/nasa/harmony-autotester/releases/tag/1.4.0
[v1.3.0]: https://github.com/nasa/harmony-autotester/releases/tag/1.3.0
[v1.2.2]: https://github.com/nasa/harmony-autotester/releases/tag/1.2.2
[v1.2.1]: https://github.com/nasa/harmony-autotester/releases/tag/1.2.1
[v1.2.0]: https://github.com/nasa/harmony-autotester/releases/tag/1.2.0
[v1.1.0]: https://github.com/nasa/harmony-autotester/releases/tag/1.1.0
[v1.0.0]: https://github.com/nasa/harmony-autotester/releases/tag/1.0.0
