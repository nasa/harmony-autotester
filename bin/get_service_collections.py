"""Print the collections associated with a test directory's Harmony service(s).

This is a local development helper. It looks up the UMM-S concept ID mapped
to the given test directory in the service mapping file for
`EARTHDATA_ENVIRONMENT`, queries CMR GraphQL for every collection associated
with that service, and prints the result as JSON in the format expected by the
`SERVICE_COLLECTIONS` environment variable, e.g.:

    export SERVICE_COLLECTIONS=$(python bin/get_service_collections.py tests/hybig)
    pytest tests/hybig

Required environment variables: `EARTHDATA_ENVIRONMENT` (`production` or
`UAT`), `EARTHDATA_USERNAME` and `EARTHDATA_PASSWORD`. `CMR_GRAPHQL_URL` and
`EARTHDATA_URL` default from the environment but may be overridden.

"""

import json
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path

from get_all_services import get_authenticated_session, get_service_collections
from get_service_test_directory import PRODUCTION_SERVICE_MAPPING, UAT_SERVICE_MAPPING

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent

ENVIRONMENT_DEFAULTS = {
    'production': {
        'CMR_GRAPHQL_URL': 'https://graphql.earthdata.nasa.gov/api',
        'EARTHDATA_URL': 'https://urs.earthdata.nasa.gov',
        'SERVICE_MAPPING': PRODUCTION_SERVICE_MAPPING,
    },
    'UAT': {
        'CMR_GRAPHQL_URL': 'https://graphql.uat.earthdata.nasa.gov/api',
        'EARTHDATA_URL': 'https://uat.urs.earthdata.nasa.gov',
        'SERVICE_MAPPING': UAT_SERVICE_MAPPING,
    },
}


def get_service_concept_id(test_directory: str, mapping_file: Path) -> str | None:
    """Reverse-lookup the UMM-S concept ID mapped to a test directory."""
    with open(mapping_file, encoding='utf-8') as file_handler:
        service_mapping = json.load(file_handler)

    for concept_id, mapped_directory in service_mapping.items():
        if mapped_directory == test_directory:
            return concept_id

    return None


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit('Usage: python bin/get_service_collections.py tests/<service>')
    test_directory = sys.argv[1].rstrip('/')
    test_directory = sys.argv[1].rstrip('/')
    earthdata_environment = os.environ['EARTHDATA_ENVIRONMENT']
    defaults = ENVIRONMENT_DEFAULTS[earthdata_environment]
    mapping_file = REPOSITORY_ROOT / defaults['SERVICE_MAPPING']

    service_concept_id = get_service_concept_id(test_directory, mapping_file)

    if service_concept_id is None:
        sys.exit(
            f'{test_directory} is not registered for {earthdata_environment} '
            f'in {mapping_file}'
        )

    authenticated_session = get_authenticated_session(
        os.environ.get('EARTHDATA_URL', defaults['EARTHDATA_URL']),
        os.environ['EARTHDATA_USERNAME'],
        os.environ['EARTHDATA_PASSWORD'],
    )
    cmr_graphql_url = os.environ.get('CMR_GRAPHQL_URL', defaults['CMR_GRAPHQL_URL'])

    # get_service_collections prints progress and errors to stdout. Send those
    # to stderr so that only the JSON is captured by `$(...)`.
    with redirect_stdout(sys.stderr):
        collections = get_service_collections(
            authenticated_session, cmr_graphql_url, service_concept_id
        )

    print(json.dumps(collections))
