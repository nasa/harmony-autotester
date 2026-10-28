"""pytest suite for the sds/HOSS-regridder-reformatter service chain."""

import earthaccess
from harmony import BBox, Collection

from tests.conftest import AutotesterRequest
from tests.umm_g_utilities import generate_partial_spatial_box


def test_hoss_regridder_reformatter(
    failed_tests, harmony_client, service_collection, earthaccess_login
):
    """Run a bounding box subset request with GeoTIFF output.

    To get GeoTIFF output the request is routed to sds/HOSS-regridder-reformatter.
    This test requests all variables and net2cog will only convert gridded variables.

    """
    try:
        harmony_request = None

        granules = earthaccess.search_data(
            collection_concept_id=service_collection['concept_id'], count=1
        )
        assert granules, 'The collection has no granules'

        west, east, south, north = generate_partial_spatial_box(granules, 25.0)

        harmony_request = AutotesterRequest(
            collection=Collection(id=service_collection['concept_id']),
            granule_id=[granules[0]['meta']['concept-id']],
            spatial=BBox(west, south, east, north),
            variables=['all'],
            format='image/tiff',
        )

        # Submit the job and get the JSON output once completed
        harmony_job_id = harmony_client.submit(harmony_request)
        result_json = harmony_client.result_json(harmony_job_id)

        # Check the response was successful
        assert result_json['status'] == 'successful', (
            f'Harmony request failed:\n\n{result_json["message"]}'
        )

        # Check the URLs for results are all of the expected type.
        ensure_correct_files_created(result_json['links'], result_json['message'])
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


def ensure_correct_files_created(harmony_result_json_links: list[dict], message: str):
    """Check the output files.

    net2cog writes one GeoTIFF per converted variable, each with the
    `_reformatted.tif` suffix. The number of variables that can be converted
    depends on the granule, so at least one output file is required.

    """
    data_links = [link for link in harmony_result_json_links if link['rel'] == 'data']
    assert data_links, f'Expected at least 1 GeoTIFF output file:\n\n{message}'

    assert all(link['href'].endswith('_reformatted.tif') for link in data_links), (
        'Not all data links are reformatted GeoTIFF files'
    )
