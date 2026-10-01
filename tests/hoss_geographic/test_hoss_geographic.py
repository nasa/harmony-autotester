"""pytest suite for the sds/HOSS-geographic service chain."""

import earthaccess
from harmony import BBox, Collection

from tests.conftest import AutotesterRequest, get_configured_variable_names
from tests.umm_g_utilities import generate_partial_spatial_box


def test_hoss_geographic(
    failed_tests, harmony_client, service_collection, earthaccess_login
):
    """Run a variable and bounding box subset request for HOSS-geographic."""
    try:
        harmony_request = None

        granules = earthaccess.search_data(
            collection_concept_id=service_collection['concept_id'], count=1
        )
        assert granules, 'The collection has no granules'

        west, east, south, north = generate_partial_spatial_box(granules, 25.0)

        # Request up to two configured variables, or all variables if the
        # collection has no configured variables.
        variables = get_configured_variable_names(
            harmony_client, service_collection['concept_id']
        )[0:2] or ['all']

        harmony_request = AutotesterRequest(
            collection=Collection(id=service_collection['concept_id']),
            granule_id=[granules[0]['meta']['concept-id']],
            spatial=BBox(west, south, east, north),
            variables=variables,
            format='application/netcdf',
        )

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


def ensure_correct_files_created(harmony_result_json_links: list[dict]):
    """Check the output file.

    There should be one output data file that its name ends with HOSS subsetting
    suffix `_subsetted.nc4`.

    """
    data_links = [link for link in harmony_result_json_links if link['rel'] == 'data']
    assert len(data_links) == 1, 'Should have 1 subsetted output file'

    assert data_links[0]['href'].endswith('_subsetted.nc4'), (
        'Data link is not a subsetted NetCDF-4 file'
    )
