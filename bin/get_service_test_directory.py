"""A module to retrieve the test directory for a given service.

The directory name will be written to the GitHub workflow environment variables
as `test_directory`. If there is no available test suite for the specified UMM-S
record, this module will not create an environment variable.

To enable a test suite to be run, please add items to the files specified via
`PRODUCTION_SERVICE_MAPPING` and/or `UAT_SERVICE_MAPPING` as appropriate.

See `README.md` for full guidance on configuring a set of tests for a service.

"""

import json
import os

PRODUCTION_SERVICE_MAPPING = 'bin/production_service_mapping.json'
UAT_SERVICE_MAPPING = 'bin/uat_service_mapping.json'


def get_service_test_directory(service_concept_id: str) -> str | None:
    """Get test directory from environment service mapping."""
    earthdata_environment = os.environ.get('EARTHDATA_ENVIRONMENT')

    if earthdata_environment == 'UAT':
        mapping_file_path = UAT_SERVICE_MAPPING
    else:
        mapping_file_path = PRODUCTION_SERVICE_MAPPING

    with open(mapping_file_path, encoding='utf-8') as mapping_file:
        service_mapping = json.load(mapping_file)

    return service_mapping.get(service_concept_id)


def output_service_test_directory(service_test_directory: str) -> None:
    """Write name of service test directory to an environment variable."""
    with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as env_file:
        print(f'test_directory={service_test_directory}', file=env_file)


if __name__ == '__main__':
    """Identify test directory for service and write to environment variable."""
    service_concept_id = os.environ.get('SERVICE_CONCEPT_ID')
    service_test_directory = get_service_test_directory(service_concept_id)

    if service_test_directory:
        output_service_test_directory(service_test_directory)
