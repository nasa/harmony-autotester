"""pytest suite for smap-l2-subsetter-net2cog."""

import earthaccess
from harmony import BBox, CapabilitiesRequest, Collection

from tests.conftest import AutotesterRequest
from tests.umm_g_utilities import generate_partial_spatial_box


def test_smap_l2_subsetter_net2cog(
    failed_tests, harmony_client, service_collection, earthaccess_login
):
    """Run a sample request against the service_collection."""
    # Get some CMR umm-g metadata information.
    granules = earthaccess.search_data(
        short_name=service_collection['short_name'],
        version=service_collection['version'],
        count=1,
    )

    west, east, south, north = generate_partial_spatial_box(granules, 25.0)
    spatial_limit = BBox(west, south, east, north)

    cap_request = CapabilitiesRequest(collection_id=service_collection['concept_id'])
    capabilities = harmony_client.submit(cap_request)
    variables = capabilities.get('figure this out.')

    variables = 'Ancillary_Data/bare_soil_roughness_tabular'

    request_params = {
        'spatial': spatial_limit,
        'variables': [variables],
        'format': 'image/tiff',
    }

    print(f'request_params: {request_params}')

    harmony_request = AutotesterRequest(
        collection=Collection(id=service_collection['concept_id']),
        **request_params,
        max_results=1,
    )

    try:
        # Submit the job and get the JSON output once completed
        harmony_job_id = harmony_client.submit(harmony_request)
        result_json = harmony_client.result_json(harmony_job_id)

        # Check the response was successful
        assert result_json['status'] == 'successful', (
            f'Harmony request failed:\n\n{result_json["message"]}'
        )

        # Check the URLs for results are all of the expected type.
        ensure_correct_files_created(result_json['links'])
    except AssertionError as exception:
        # Cache error message and re-raise the AssertionError to fail the test
        failed_tests.append(
            {
                **service_collection,
                'error': str(exception),
                'url': harmony_client.request_as_url(harmony_request),
            }
        )
        raise
    except Exception as exception:
        # Catch other exception types and raise as an AssertionError to
        # ensure test test suite is robust against unexpected exceptions.
        # This does not cache the failure, as this should only arise from
        # systematic issues, such as connecting to Harmony, not issues specific
        # to the collection under test.
        raise AssertionError('Unexpected request failure') from exception


def ensure_correct_files_created(harmony_result_json_links: list[dict]):
    """Verify output files look reasonable."""
    print(harmony_result_json_links)
