"""Test fixtures and classes to be re-used for different test suites.

Modules in the test suite subdirectories will have access to this
conftest.py, which sets up common functionality for:

* A Harmony Client.
* The list of collections associated with the service under test.
* A cache for test failures, to be written out at the end of testing.

Note: With the use of the `pytest-xdist` plugin, session scoped fixtures are
not shared between workers. This is particularly important for the
`failed_tests` fixture that aggregates failures and output test files.

"""

import json
import os
from glob import glob
from os import remove
from pathlib import Path

import earthaccess
import pytest
from harmony import CapabilitiesRequest, Client, Environment, Request

environment_mapping = {
    'production': Environment.PROD,
    'UAT': Environment.UAT,
}

earthaccess_mapping = {
    'production': earthaccess.PROD,
    'UAT': earthaccess.UAT,
}


class AutotesterRequest(Request):
    """Child class of harmony-py Requests adding harmony-autotester label."""

    def __init__(self, **kwargs):
        """Propagate kwargs and add a "harmony-autotester" label."""
        labels = kwargs.get('labels', [])
        labels.append('harmony-autotester')
        super().__init__(**kwargs, labels=labels)


service_collections = json.loads(os.environ.get('SERVICE_COLLECTIONS', '[]'))


def pytest_sessionfinish(session, exitstatus):
    """A `pytest` hook that runs at the end of the test sessions.

    Note: This includes sessions on each `pytest-xdist` worker node, as well as
    the overall controller node.

    After the workers finish, the controller executes this hook and generates
    the final output file with all failures from all workers.

    If there is no `TEST_DIRECTORY` environment variable, output files will be
    stored in the directory from which the `pytest` command was executed. This
    environment variable will always be set in the GitHub CI/CD.

    If a `test_output.json` file already exists in the directory, it will be
    clobbered by this hook. This is important when the `TEST_DIRECTORY`
    environment variable is not set.

    """
    if hasattr(session.config, 'workerinput'):
        # Do not try to combine outputs at the end of a worker's session, only
        # when this hook is called by the controller.
        return

    test_directory = Path(os.environ.get('TEST_DIRECTORY') or session.config.rootpath)
    combined_test_output = []

    for worker_test_output_file in glob(f'{test_directory}/test_output_*.json'):
        with open(worker_test_output_file) as file_handler:
            combined_test_output.extend(json.load(file_handler))

        # Clean up worker-specific output files:
        remove(worker_test_output_file)

    with open(f'{test_directory}/test_output.json', 'w') as file_handler:
        json.dump(combined_test_output, file_handler, indent=2)


@pytest.fixture(
    params=service_collections,
    ids=[
        f'{collection["short_name"]}-{collection["version"]}-{collection["concept_id"]}'
        for collection in service_collections
    ],
    scope='session',
)
def service_collection(request):
    """Fixture to parametrize tests to iterate over associated collections."""
    return request.param


@pytest.fixture(scope='session')
def harmony_client():
    """A harmony-py Client object for making requests."""
    environment_string = os.environ.get('EARTHDATA_ENVIRONMENT')
    earthdata_username = os.environ.get('EARTHDATA_USERNAME')
    earthdata_password = os.environ.get('EARTHDATA_PASSWORD')
    return Client(
        auth=(earthdata_username, earthdata_password),
        env=environment_mapping.get(environment_string),
    )


@pytest.fixture(scope='session')
def earthaccess_login():
    """An earthaccess Client object for accessing metadata."""
    environment_string = os.environ.get('EARTHDATA_ENVIRONMENT')
    return earthaccess.login(
        strategy='environment', system=earthaccess_mapping.get(environment_string)
    )


@pytest.fixture(scope='session')
def test_output_file(request, worker_id):
    """The path to where the failed test information should be written.

    Defaults to the directory from which the `pytest` command was executed if
    `TEST_DIRECTORY` is not set (local development).

    Note: `pytest-xdist` will set worker IDs with format "gw0", "gw1", etc, if
    parallelisation is enabled. If the plugin is disabled (n=0), or `pytest` is
    executed without specifying the number of workers, `worker_id="master"`.

    """
    test_directory = Path(os.environ.get('TEST_DIRECTORY') or request.config.rootpath)
    return f'{test_directory}/test_output_{worker_id}.json'


@pytest.fixture(scope='session')
def failed_tests(test_output_file):
    """A fixture to accumulate failed test results.

    Note: The `pytest-xdist` plugin will not share session-based fixtures
    across workers, so there will be an instance of the `failed_tests` worker
    for each fixture. The outputs from each worker are combined using the
    `pytest_sessionfinish` hook.

    """
    failed_test_information = []
    yield failed_test_information
    with open(test_output_file, 'w', encoding='utf-8') as file_handler:
        json.dump(failed_test_information, file_handler, indent=2)


def get_configured_variable_names(
    harmony_client: Client, collection_id: str
) -> list[str]:
    """Get the name of the configured variables for the collection.

    Calls Harmony's capabilities endpont for the collection and returns a list
    of all configured variable names.
    """
    cap_request = CapabilitiesRequest(collection_id=collection_id)
    capabilities = harmony_client.submit(cap_request)
    return [v['name'] for v in capabilities.get('variables')]
