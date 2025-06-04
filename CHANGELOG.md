# Changelog

The Harmony Autotester follows semantic versioning. All notable changes to this
project will be documented in this file. The format is based on [Keep a
Changelog](http://keepachangelog.com/en/1.0.0/).

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

[Unreleased]: https://github.com/nasa/harmony-autotester/compare/1.2.1...HEAD
[v1.2.1]: https://github.com/nasa/harmony-autotester/releases/tag/1.2.1
[v1.2.0]: https://github.com/nasa/harmony-autotester/releases/tag/1.2.0
[v1.1.0]: https://github.com/nasa/harmony-autotester/releases/tag/1.1.0
[v1.0.0]: https://github.com/nasa/harmony-autotester/releases/tag/1.0.0
