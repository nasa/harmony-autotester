"""Module to identify all Harmony services and their associated collections.

The information retrieved is written to the file containing GitHub environment
variables, specified by the `GITHUB_OUTPUT` environment variable. This is done
so that later workflow jobs can use the output as the basis for a matrix to
parallelise testing.

"""

import json
import os

import requests


def get_edl_bearer_token(edl_url: str, edl_user: str, edl_password: str) -> str:
    """Retrieve an Earthdata Login (EDL) token.

    This function uses an EDL username and password, which are stored in the
    GitHub repository as secrets, instead of relying on a .netrc file.

    """
    existing_tokens_response = requests.get(
        f'{edl_url}/api/users/tokens',
        headers={'Content-type': 'application/json'},
        auth=(edl_user, edl_password),
        timeout=10,
    )
    existing_tokens_response.raise_for_status()
    existing_tokens_json = existing_tokens_response.json()

    if len(existing_tokens_json) == 0:
        new_token_response = requests.post(
            f'{edl_url}/api/users/token',
            headers={'Content-type': 'application/json'},
            auth=(edl_user, edl_password),
            timeout=10,
        )
        new_token_response.raise_for_status()
        new_token_json = new_token_response.json()
        edl_token = new_token_json['access_token']
    else:
        edl_token = existing_tokens_json[0]['access_token']

    return edl_token


def get_authenticated_session(
    edl_url: str, edl_user: str, edl_password: str
) -> requests.Session:
    """Create a `requests.Session` object that is authorised via Earthdata login.

    The returned session object will contain an `Authorization` header
    containing an EDL bearer token, which will be automatically used in all
    requests made via that session.

    """
    edl_bearer_token = get_edl_bearer_token(edl_url, edl_user, edl_password)
    session = requests.session()
    session.headers.update(
        {
            'Authorization': f'Bearer {edl_bearer_token}',
        }
    )
    return session


def get_service_collections(
    authenticated_session: requests.Session,
    cmr_graphql_url: str,
    service_concept_id: str,
) -> list[dict[str, str]]:
    """Identify all collections associated with the given Harmony service.

    Perform a Service query against CMR GraphQL to retrieve all collections
    associated with the service, as specified by the service concept ID.

    """
    print(f'Retrieving collections for {service_concept_id}')
    query_parameters = {
        'serviceParams': {
            'conceptId': service_concept_id,
        },
        'collectionsParams': {'cursor': None, 'limit': 100},
    }

    query_string = """
    query Service($serviceParams: ServiceInput, $collectionsParams: CollectionsInput) {
      service(params: $serviceParams) {
        collections(params: $collectionsParams) {
          items {
            conceptId
            shortName
            version
          }
          cursor
        }
      }
    }
    """

    request_json = {
        'operationName': 'Service',
        'query': query_string,
        'variables': query_parameters,
    }

    cursor = 'not null'

    # The error count and limit prevent infinite loops from repeated errors:
    max_errors = 3
    error_count = 0

    collections = []
    # Perform paginated request - this ensures services associated with many
    # collections will still succeed.
    # Requests will continue until all services have been retrieved
    while error_count < max_errors and cursor is not None:
        cmr_graph_response = authenticated_session.post(
            url=cmr_graphql_url, json=request_json, timeout=10
        )

        if cmr_graph_response.ok:
            json_data = cmr_graph_response.json()

            # Extract collection information for service
            collections.extend(
                [
                    {
                        'concept_id': collection['conceptId'],
                        'short_name': collection['shortName'],
                        'version': collection['version'],
                    }
                    for collection in json_data['data']['service']['collections'][
                        'items'
                    ]
                ]
            )

            # Update the cursor for paginated requests
            cursor = json_data['data']['service']['collections']['cursor']
            request_json['variables']['collectionsParams']['cursor'] = cursor
        else:
            error_count += 1
            print(f'response status code: f{cmr_graph_response.status_code}')
            print(f'response : {cmr_graph_response.content}')

    return collections


def get_all_harmony_services(
    authenticated_session: requests.Session,
    cmr_graphql_url: str,
) -> list[dict]:
    """Retrieve all Harmony services and their associated collections.

    First use CMR GraphQL to identify all UMM-S records with a type of "harmony".
    Next, for each service, query for all associated collections. This is not
    performed as a single query, as pagination of nested items did not appear
    to be working as expected.

    A list output is chosen in preference to a dictionary for compatibility with
    the GitHub Action matrix functionality.

    """
    print('\nRetrieving all Harmony services')
    query_parameters = {
        'servicesParams': {
            'limit': 100,
            'type': 'harmony',
        },
    }

    query_string = """
    query Services($servicesParams: ServicesInput) {
      services(params: $servicesParams) {
        count
        items {
          name
          conceptId
          version
          collections {
            count
          }
        }
        cursor
      }
    }
    """

    request_json = {
        'operationName': 'Services',
        'query': query_string,
        'variables': query_parameters,
    }

    # Begin with non-null cursor to satisfy while loop
    cursor = 'not null'

    # The error count and limit prevent infinite loops from repeated errors:
    error_count = 0
    max_errors = 3

    harmony_services = []

    while error_count < max_errors and cursor is not None:
        cmr_graph_response = authenticated_session.post(
            url=cmr_graphql_url, json=request_json, timeout=10
        )

        if cmr_graph_response.ok:
            json_data = cmr_graph_response.json()

            # Add service information to harmony_services aggregator:
            harmony_services.extend(
                [
                    {
                        'concept_id': service['conceptId'],
                        'name': service['name'],
                        'version': service['version'],
                        'collection_count': service['collections']['count'],
                    }
                    for service in json_data['data']['services']['items']
                ]
            )

            # Update the cursor for paginated requests
            cursor = json_data['data']['services']['cursor']
            request_json['variables']['servicesParams']['cursor'] = cursor
        else:
            error_count += 1
            print(f'response status code: f{cmr_graph_response.status_code}')
            print(f'response : {cmr_graph_response.content}')

    # Return list that also contains information on all collections associated
    # with each service:
    return [
        {
            **harmony_service,
            'collections': get_service_collections(
                authenticated_session,
                cmr_graphql_url,
                harmony_service['concept_id'],
            ),
        }
        for harmony_service in harmony_services
    ]


def output_all_services(harmony_services: list[dict]) -> None:
    """Write service information to a GitHub environment variable.

    This function accesses the GitHub environment file listed at the `GITHUB_OUTPUT`
    environment variable and saved the Harmony service information as a string
    of JSON.

    This JSON will then be accessible to later workflow jobs as steps.

    """
    with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as file_handler:
        print(f'all_services={json.dumps(harmony_services)}', file=file_handler)


if __name__ == '__main__':
    # Retrieve environment-specific information:
    cmr_graphql_url = os.environ.get('CMR_GRAPHQL_URL')
    edl_url = os.environ.get('EDL_URL')
    edl_user = os.environ.get('EDL_USER')
    edl_password = os.environ.get('EDL_PASSWORD')

    # Retrieve all service information and write it to the file listed as
    # GITHUB_OUTPUT.
    authenticated_session = get_authenticated_session(edl_url, edl_user, edl_password)
    all_services = get_all_harmony_services(authenticated_session, cmr_graphql_url)
    output_all_services(all_services)
