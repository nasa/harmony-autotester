"""Test fixtures and classes to be re-used for different test suites.

Modules in the test suite subdirectories will have access to this
conftest.py, which sets up common functionality for:

* A Harmony Client.
* The list of collections associated with the service under test.
* A cache for test failures, to be written out at the end of testing.

Note: With the use of the `pytest-xdist` plugin, session scoped fixtures are
not shared between workers. This is particularly important for the
`failed_tests` fixture, which are sent from each worker to the controller node
and written to a single output file.

"""

import json
import os
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


failed_tests_key = pytest.StashKey[list[dict]]()


def pytest_configure(config: pytest.Config) -> None:
    """Create a list to accumulate failed test information."""
    config.stash[failed_tests_key] = []


@pytest.hookimpl(optionalhook=True)
def pytest_testnodedown(node, error) -> None:
    """Collect test failures sent by a finished `pytest-xdist` worker.

    This hook is only called on the controller node. Each worker sends the
    contents of the `failed_tests` fixture to the controller via `workeroutput`
    in `pytest_sessionfinish`. If a worker crashed, `workeroutput` may not be
    set. `pytest` will know which tests have failed but the `failed_tests`
    information from that node prior to the crash will be lost.

    """
    node.config.stash[failed_tests_key].extend(
        getattr(node, 'workeroutput', {}).get('failed_tests', [])
    )


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
    failed_tests = session.config.stash[failed_tests_key]

    if hasattr(session.config, 'workerinput'):
        # This is a worker node. Set failed_tests in the workeroutput and do
        # not progress to write final output file
        session.config.workeroutput['failed_tests'] = failed_tests
        return

    test_directory = Path(os.environ.get('TEST_DIRECTORY') or session.config.rootpath)

    with open(f'{test_directory}/test_output.json', 'w') as file_handler:
        json.dump(failed_tests, file_handler, indent=2)


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
def failed_tests(request):
    """A fixture to accumulate failed test results.

    Note: The `pytest-xdist` plugin will not share session-based fixtures
    across workers, each worker has its own `failed_tests` list. These lists
    are combined on the controller node via `pytest_testnodedown`.

    If a worker crashes it will be automatically restarted to continue any
    remaining tests. But the restarted worker will also have a fresh version of
    any session-scoped fixtures, like `failed_tests`, and so any test failures
    discovered in a worker prior to it failing will be missing from the final
    output.

    """
    return request.config.stash[failed_tests_key]


def get_configured_variable_names(
    harmony_client: Client, collection_id: str
) -> list[str]:
    """Get the name of the configured variables for the collection.

    Calls Harmony's capabilities endpont for the collection and returns a list
    of all configured variable names. If the collection has no configured variables,
    returns ['all'], so a request made with the result will ask all variables.
    """
    cap_request = CapabilitiesRequest(collection_id=collection_id)
    capabilities = harmony_client.submit(cap_request)
    return [v['name'] for v in capabilities.get('variables')] or ['all']
