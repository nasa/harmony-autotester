"""Module to create or update GitHub issues for test failures.

* First this script will retrieve all open GitHub issues that also have a label
for the service (based on the name from the UMM-S record).
* Next the `test_output.json` is parsed to extract all failed tests.
* For every failed test, the open GitHub issues are checked. If there is an
  existing open GitHub issue, it is updated with a most recent failure data.
  If there is no matching GitHub issue (e.g., no open GitHub issue with both
  the service label and the collection label for the failed collection), a new
  GitHub issue is created.
* Finally, a list of all open GitHub issues for the service is created that
  does not have a test failure for the collection the issue is labelled with.
  Those issues will be updated to list the most recent success date, allowing a
  data providing curator to make an assessment for if that issue should be
  closed.

Note: This functionality all relies labelling of GitHub issues based on mutable
fields of CMR records (UMM-S name, UMM-C short name, UMM-C version). While
concept IDs would provide a more reliable long term reference, these labels are
end-user facing and so should use public-facing fields from the metadata records.

"""

import json
import os
import re
from datetime import date

import requests


def get_date_string() -> str:
    """Return ISO-8601 formatted date string."""
    return date.today().isoformat()


def get_new_issue_body(error: str) -> str:
    """Create the string body of a new GitHub issue."""
    date_string = get_date_string()
    return (
        f'```\n{error}\n```\n\n'
        f'Original failure date: {date_string}\n'
        f'Most recent failure: {date_string}'
    )


def get_updated_failing_issue_body(existing_body: str) -> str:
    """Update most recent failure date in GitHub issue body."""
    date_string = get_date_string()
    return re.sub(
        r'Most recent failure\: \d{4}-\d{2}-\d{2}',
        f'Most recent failure: {date_string}',
        existing_body,
    )


def update_github_issue_body(
    github_repository: str,
    issue_number: int,
    issue_body: str,
    github_token: str,
):
    """Publish an updated GitHub issue that only amends its body."""
    update_response = requests.patch(
        (
            f'https://api.github.com/repos/{github_repository}'
            f'/issues/{issue_number}'
        ),
        headers={
            'Accept': 'application/vnd.github+json',
            'Authorization': f'Bearer {github_token}',
        },
        json={'body': issue_body},
        timeout=10,
    )
    update_response.raise_for_status()


def get_next_paginated_url(github_response: requests.Response) -> str | None:
    """Extract URL for next set of GitHub issues from paginated response.

    Responses from the GitHub API contain a Link header. These allow for
    navigation between the first, previous, next and last pages in a paginated
    response. The 'next' link will only be present if there is at least one
    more page to retrieve.

    """
    link_header = github_response.headers.get('Link', '')

    next_url_pattern = r'<(?P<next_url>\S+)>; rel="next"'
    next_url_matches = re.search(next_url_pattern, link_header)

    if next_url_matches:
        next_url = next_url_matches.groupdict()['next_url']
    else:
        next_url = None

    return next_url


def get_test_failures(test_directory: str) -> list:
    """Read test failures from the saved JSON outputs."""
    with open(f'{test_directory}/test_output.json', encoding='utf-8') as file_handler:
        test_failures = json.load(file_handler)

    return test_failures


def has_collection_label(issue: dict, collection_label: str) -> bool:
    """Return if the issue has the specified collection label."""
    return any(label['name'] == collection_label for label in issue['labels'])


def get_collection_issue(
    open_service_issues: list[dict],
    collection_label: str,
) -> dict:
    """Retrieve an open issue for the service and collection combination."""
    return next(
        (
            issue
            for issue in open_service_issues
            if has_collection_label(issue, collection_label)
        ),
        None,
    )


def get_collection_label(failure_information: dict[str, str]) -> str:
    """Create a label containing the collection short name and version.

    While these are mutable fields in the UMM-C schema, the label created is
    public-facing, and so the more human-readable combination of the short name
    and version are used: "<short name> <version>".

    """
    return ' '.join(
        [
            failure_information['short_name'],
            failure_information['version'],
        ]
    )


def create_or_update_failure_github_issue(
    failure_information: dict[str, str],
    service_label: str,
    open_service_issues: list[dict],
    github_repository: str,
    github_token: str,
):
    """Create or update a GitHub issue for the collection test failure."""
    collection_label = get_collection_label(failure_information)
    collection_issue = get_collection_issue(open_service_issues, collection_label)

    if not collection_issue:
        # Create a new issue
        creation_response = requests.post(
            f'https://api.github.com/repos/{github_repository}/issues',
            headers={
                'Accept': 'application/vnd.github+json',
                'Authorization': f'token {github_token}',
            },
            json={
                'title': f'{service_label} - {collection_label}',
                'body': get_new_issue_body(failure_information['error']),
                'labels': [collection_label, service_label],
            },
            timeout=10,
        )

        creation_response.raise_for_status()
    else:
        # Update existing issue body stating most recent failure date
        update_github_issue_body(
            github_repository,
            collection_issue['number'],
            get_updated_failing_issue_body(collection_issue['body']),
            github_token,
        )


def get_open_service_issues(github_repository: str, service_label: str) -> list[dict]:
    """Query the GitHub API for all open issues with the service label.

    Parameters:

    * github_repository : str
        GitHub provided environment variable including the owner and repository,
        e.g., 'nasa/harmony-autotester'.
    * service_label : str
        The name of the service per the UMM-S record. This is used as a label
        for all issues opened relating to failures of the specific service.

    Query filters:

    * status: open
    * label: service name

    Uses GitHub pagination, and default page size of 30 issues. If there are
    more than 30 open issues with the associated label, the Link header is used
    to determine the URL for the next page of results. API requests will
    continue until the Link header is either absent or has no "next" URL.

    Note: Pull requests are also returned in the response, because PRs are
    considered issues. These are detected by the presence of the "pull_request"
    property in an issue item. The returned list from this function excludes PRs.

    """
    open_service_issues = []
    issues_url = f'https://api.github.com/repos/{github_repository}/issues'

    while issues_url:
        issues_response = requests.get(
            issues_url,
            headers={'Accept': 'application/vnd.github+json'},
            params={'state': 'open', 'labels': service_label},
            timeout=10,
        )
        issues_response.raise_for_status()
        open_service_issues.extend(issues_response.json())
        issues_url = get_next_paginated_url(issues_response)

    # Filter out pull requests in return value:
    return [issue for issue in open_service_issues if 'pull_request' not in issue]


def collection_passed_service_tests(
    service_issue: dict, test_failures: list[dict]
) -> bool:
    """Check if the open GitHub issue has a test failure from current execution.

    This helps identify when a previously failing collection-service pairing is
    now passing tests.

    """
    matching_test_failure = False

    for test_failure in test_failures:
        collection_label = get_collection_label(test_failure)
        if any(label['name'] == collection_label for label in service_issue['labels']):
            matching_test_failure = True

    return not matching_test_failure


def get_issues_without_failures(
    github_issues: list[dict],
    test_failures: list[dict],
) -> list[dict]:
    """Filter list of existing GitHub issues to only those with no current failures."""
    return [
        github_issue
        for github_issue in github_issues
        if collection_passed_service_tests(github_issue, test_failures)
    ]


def add_success_to_issue_body(
    service_issue: dict, github_repository: str, github_token: str
):
    """Add a line to GitHub issue saying the tests passed during this execution.

    The `service_issue` in this case is one of the GitHub issues retrieved by
    listing all GitHub issues with the label denoting a specific service. Only
    those GitHub issues in the list that do not have a corresponding test
    failure in the current test execution will call this function.

    """
    success_string = f'Most recent success: {get_date_string()}'

    success_pattern = r'Most recent success: \d{4}-\d{2}-\d{2}'
    success_matches = re.search(success_pattern, service_issue['body'])

    if success_matches:
        success_body = re.sub(
            success_pattern,
            success_string,
            service_issue['body'],
        )
    else:
        success_body = '\n'.join([service_issue['body'], success_string])

    update_github_issue_body(
        github_repository, service_issue['number'], success_body, github_token
    )


if __name__ == '__main__':
    github_repository = os.environ.get('GH_REPOSITORY')
    github_token = os.environ.get('GH_TOKEN')
    service_name = os.environ.get('SERVICE_NAME')
    test_directory = os.environ.get('TEST_DIRECTORY')

    # Get all open issues associated with the service
    service_issues = get_open_service_issues(github_repository, service_name)

    # Retrieve all failures for test run
    test_failures = get_test_failures(test_directory)

    # Iterate through each test failure and create or update a GitHub issue:
    for test_failure in test_failures:
        create_or_update_failure_github_issue(
            test_failure,
            service_name,
            service_issues,
            github_repository,
            github_token,
        )

    # Update body of any open GitHub issue for the service corresponding to a
    # collection that passed the current test execution.
    github_issues_without_failures = get_issues_without_failures(
        service_issues, test_failures
    )

    for github_issue in github_issues_without_failures:
        add_success_to_issue_body(github_issue, github_repository, github_token)
