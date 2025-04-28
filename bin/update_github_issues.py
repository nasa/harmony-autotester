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


def get_new_issue_body(error: str, request_url: str) -> str:
    """Create the string body of a new GitHub issue."""
    date_string = get_date_string()
    return (
        '## Failure request URL:\n'
        f'<{request_url}>\n'
        '## Failure details:\n'
        f'```\n{error}\n```\n\n'
        '## Failure results:\n'
        'Current status indicated by most recent date below:\n\n'
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
        f'https://api.github.com/repos/{github_repository}/issues/{issue_number}',
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


def has_label(issue: dict, label_name: str) -> bool:
    """Return if the issue has a label with the specified name."""
    return any(label['name'] == label_name for label in issue['labels'])


def get_collection_issue(
    open_service_issues: list[dict],
    collection_label: str,
    earthdata_environment: str,
) -> dict:
    """Retrieve an open issue for the service and collection combination.

    This function also checks that the issue has a label matching the environment
    against which the tests were run, as collections and services with the same
    names will likely be present in both UAT and production.

    """
    return next(
        (
            issue
            for issue in open_service_issues
            if has_label(issue, collection_label)
            and has_label(issue, earthdata_environment)
        ),
        None,
    )


def get_collection_label(collection_information: dict[str, str]) -> str:
    """Create a label containing the collection short name and version.

    While these are mutable fields in the UMM-C schema, the label created is
    public-facing, and so the more human-readable combination of the short name
    and version are used: "<short name> <version>".

    """
    return ' '.join(
        [
            collection_information['short_name'],
            collection_information['version'],
        ]
    )


def get_collection_provider(failure_information: dict[str, str]) -> str:
    """Retrieve the CMR provider from the concept ID of the failed collections."""
    return failure_information['concept_id'].split('-')[-1]


def create_or_update_failure_github_issue(
    failure_information: dict[str, str],
    service_label: str,
    earthdata_environment: str,
    open_service_issues: list[dict],
    github_repository: str,
    github_token: str,
):
    """Create or update a GitHub issue for the collection test failure."""
    collection_label = get_collection_label(failure_information)
    collection_issue = get_collection_issue(
        open_service_issues, collection_label, earthdata_environment
    )
    collection_provider = get_collection_provider(failure_information)

    if not collection_issue:
        # Create a new issue
        creation_response = requests.post(
            f'https://api.github.com/repos/{github_repository}/issues',
            headers={
                'Accept': 'application/vnd.github+json',
                'Authorization': f'Bearer {github_token}',
            },
            json={
                'title': f'{service_label} - {collection_label}',
                'body': get_new_issue_body(
                    failure_information['error'],
                    failure_information['url'],
                ),
                'labels': [
                    collection_label,
                    service_label,
                    collection_provider,
                    earthdata_environment,
                ],
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


def get_issue_comments(github_issue: dict) -> list[dict]:
    """Get all comments for a GitHub issue."""
    comments = []
    comments_url = github_issue['comments_url']

    while comments_url:
        comments_response = requests.get(
            comments_url,
            headers={'Accept': 'application/vnd.github+json'},
            timeout=10,
        )
        comments_response.raise_for_status()
        comments.extend(comments_response.json())
        comments_url = get_next_paginated_url(comments_response)

    return comments


def collection_did_not_fail_service_tests(
    service_issue: dict, test_failures: list[dict]
) -> bool:
    """Check if the open GitHub issue has a test failure from current execution.

    This helps identify when a previously failing collection-service pairing is
    now passing tests or disassociated from the service.

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
        if collection_did_not_fail_service_tests(github_issue, test_failures)
    ]


def get_matching_comment_id(
    issue_comments: list[dict], body_pattern: str
) -> int | None:
    """Retrieve a comment with a body matching the specified regular expression."""
    return next(
        (
            comment['id']
            for comment in issue_comments
            if re.search(body_pattern, comment['body']) is not None
        ),
        None,
    )


def create_or_update_issue_comment(
    github_repository: str,
    service_issue_number: int,
    comment_body: str,
    github_token: str,
    comment_id: int | None = None,
):
    """Create or update a comment on a GitHub issue with the specified body.

    If a `comment_id` is given, then update the comment to have the supplied
    body, otherwise create a new comment with that body.

    """
    if comment_id is not None:
        # Patch request to update comment.
        comment_response = requests.patch(
            (
                f'https://api.github.com/repos/{github_repository}/issues'
                f'/{service_issue_number}/comments/{comment_id}'
            ),
            headers={
                'Accept': 'application/vnd.github+json',
                'Authorization': f'token {github_token}',
            },
            json={'body': comment_body},
        )
    else:
        # Create a new comment:
        comment_response = requests.post(
            (
                f'https://api.github.com/repos/{github_repository}/issues'
                f'/{service_issue_number}/comments'
            ),
            headers={
                'Accept': 'application/vnd.github+json',
                'Authorization': f'token {github_token}',
            },
            json={'body': comment_body},
        )

    comment_response.raise_for_status()


def add_success_issue_comment(
    service_issue: dict, github_repository: str, github_token: str
):
    """Add a comment to GitHub issue saying the tests passed during this execution.

    The `service_issue` in this case is one of the GitHub issues retrieved by
    listing all GitHub issues with the label denoting a specific service. Only
    those GitHub issues in the list that do not have a corresponding test
    failure in the current test execution, and still have  will call this function.

    If the issue has a previous comment saying that the tests succeeded, the
    date on that comment will be updated.

    """
    success_string = f'Most recent success: {get_date_string()}'
    success_pattern = r'Most recent success: \d{4}-\d{2}-\d{2}'

    issue_comments = get_issue_comments(service_issue)
    success_comment_id = get_matching_comment_id(issue_comments, success_pattern)

    create_or_update_issue_comment(
        github_repository,
        service_issue['number'],
        success_string,
        github_token,
        success_comment_id,
    )


def add_disassociation_issue_comment(
    service_issue: dict,
    github_repository: str,
    github_token: str,
):
    """Add a comment to GitHub issue saying the collection/service are not associated.

    The `service_issue` in this case is one of the GitHub issues retrieved by
    listing all GitHub issues with the label denoting a specific service. Only
    those GitHub issues in the list that do not have a corresponding test
    failure in the current test execution will call this function.

    If the issue has a previous comment saying that the service and collection
    are not associated, the date on that comment will be updated.

    """
    disassociation_string = (
        f'Collection/service disassociation detected: {get_date_string()}'
    )
    disassociation_pattern = (
        r'Collection/service disassociation detected: \d{4}-\d{2}-\d{2}'
    )

    issue_comments = get_issue_comments(service_issue)
    disassociation_comment_id = get_matching_comment_id(
        issue_comments, disassociation_pattern
    )

    create_or_update_issue_comment(
        github_repository,
        service_issue['number'],
        disassociation_string,
        github_token,
        disassociation_comment_id,
    )


def is_github_issue_for_associated_collection(
    github_issue: dict,
    service_collections: list[dict],
    earthdata_environment: str,
) -> bool:
    """Check if the GitHub issue matches any currently associated collections.

    This check will check if the collection label ("short name - version") of
    the GitHub issue matches any label for associated collections. The check
    also ensures that the labels for the GitHub issue
    """
    github_issue_labels = set(label['name'] for label in github_issue['labels'])
    return any(
        {get_collection_label(collection), earthdata_environment}.issubset(
            github_issue_labels
        )
        for collection in service_collections
    )


if __name__ == '__main__':
    earthdata_environment = os.environ.get('EARTHDATA_ENVIRONMENT')
    github_repository = os.environ.get('GH_REPOSITORY')
    github_token = os.environ.get('GH_TOKEN')
    service_collections = json.loads(os.environ.get('SERVICE_COLLECTIONS'))
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
            earthdata_environment,
            service_issues,
            github_repository,
            github_token,
        )

    # Add appropriate comment to any open GitHub issue for the service
    # corresponding to a collection that did not fail during the current test
    # execution. This can occur when:
    #
    # 1) The tests pass.
    # 2) A collection is no longer associated with the service, and wasn't tested.
    github_issues_without_failures = get_issues_without_failures(
        service_issues, test_failures
    )

    for github_issue in github_issues_without_failures:
        if is_github_issue_for_associated_collection(
            github_issue, service_collections, earthdata_environment
        ):
            add_success_issue_comment(github_issue, github_repository, github_token)
        else:
            add_disassociation_issue_comment(
                github_issue, github_repository, github_token
            )
