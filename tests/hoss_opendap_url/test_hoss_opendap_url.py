"""pytest suite for the sds/hoss-opendap-url service chain."""

import earthaccess
from harmony import BBox, Collection

from tests.conftest import AutotesterRequest, get_configured_variable_names
from tests.umm_g_utilities import generate_partial_spatial_box


def test_hoss_opendap_url(
    failed_tests, harmony_client, service_collection, earthaccess_login
):
    """Run a variable and bounding box subset request for an OPeNDAP URL."""
    try:
        harmony_request = None

        granules = earthaccess.search_data(
            collection_concept_id=service_collection['concept_id'], count=1
        )
        assert granules, 'The collection has no granules'

        west, east, south, north = generate_partial_spatial_box(granules, 25.0)

        # Request up to two configured variables (all variables if none are configured).
        variables = get_configured_variable_names(
            harmony_client, service_collection['concept_id']
        )[0:2]

        harmony_request = AutotesterRequest(
            collection=Collection(id=service_collection['concept_id']),
            granule_id=[granules[0]['meta']['concept-id']],
            spatial=BBox(west, south, east, north),
            variables=variables,
            format='application/x-netcdf4;profile=opendap_url',
        )

        # Submit the job and get the JSON output once completed
        harmony_job_id = harmony_client.submit(harmony_request)
        result_json = harmony_client.result_json(harmony_job_id)

        # Check the response was successful
        assert result_json['status'] == 'successful', (
            f'Harmony request failed:\n\n{result_json["message"]}'
        )

        # Check the result is an OPeNDAP request URL, not a staged file.
        ensure_opendap_url_returned(result_json['links'], result_json['message'])
    except AssertionError as exception:
        # Cache error message and re-raise the AssertionError to fail the test
        url = (
            'NOT_APPLICABLE'
            if harmony_request is None
            else harmony_client.request_as_url(harmony_request)
        )

        failed_tests.append(
            {
                **service_collection,
                'error': str(exception),
                'url': url,
            }
        )
        raise
    except Exception as exception:
        # Catch other exception types and raise as an AssertionError to
        # ensure the test suite is robust against unexpected exceptions.
        # This does not cache the failure, as this should only arise from
        # systematic issues, such as connecting to Harmony, not issues specific
        # to the collection under test.
        raise AssertionError('Unexpected request failure') from exception


def ensure_opendap_url_returned(harmony_result_json_links: list[dict], message: str):
    """Check the output link.

    HOSS returns the unexecuted OPeNDAP request URL as the only data link: a
    DAP4 request for the `.dap.nc4` response of the granule, with the subset
    in a `dap4.ce` constraint expression.

    """
    data_links = [link for link in harmony_result_json_links if link['rel'] == 'data']
    assert len(data_links) == 1, (
        f'Expected 1 OPeNDAP URL, but found {len(data_links)}:\n\n{message}'
    )

    assert '.dap.nc4?dap4.ce=' in data_links[0]['href'], (
        f'Data link is not an OPeNDAP DAP4 request URL:\n\n{data_links[0]["href"]}'
    )
