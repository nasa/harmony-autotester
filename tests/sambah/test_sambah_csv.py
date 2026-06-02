"""pytest suite for Harmony casper converter in sambah chain."""

import earthaccess
from harmony import BBox, Collection

from tests.conftest import AutotesterRequest
from tests.umm_g_utilities import (
    generate_partial_spatial_box,
)


def test_sambah_casper(
    failed_tests, harmony_client, service_collection, earthaccess_login
):
    """Run a request against sambah-casper chain and make sure it is successful.

    As a lightweight example, this test will check the Harmony request
    returned a successful status and the output STAC contains only expected
    files. No outputs will be downloaded for further verification to minimise
    overall runtime of the test suite.

    Test fixtures are retrieved from `tests/conftest.py`, which contains
    fixtures common to all Harmony services under test.

    """
    try:
        harmony_request = None

        granules = earthaccess.search_data(
            collection_concept_id=service_collection['concept_id'], count=1
        )
        assert granules, 'The collection has no granules'

        selected_granule = [granules[0]]

        granule_id = selected_granule[0]['meta']['concept-id']

        # Want output box to be 60% of orginal
        west, east, south, north = generate_partial_spatial_box(
            selected_granule,
            output_size=60.0,
        )

        harmony_request = AutotesterRequest(
            collection=Collection(id=service_collection['concept_id']),
            spatial=BBox(west, south, east, north),
            granule_id=granule_id,
            format='text/csv',
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
        # ensure test test suite is robust against unexpected exceptions.
        # This does not cache the failure, as this should only arise from
        # systematic issues, such as connecting to Harmony, not issues specific
        # to the collection under test.
        raise AssertionError('Unexpected request failure') from exception


def ensure_correct_files_created(harmony_result_json_links: list[dict]):
    """Helper function to check available data links in Harmony results JSON.

    Will ensure:

    * One "data" file is included in the output STAC.
    * Output file has the expected tags in the filename.

    """
    data_links = [link for link in harmony_result_json_links if link['rel'] == 'data']
    assert len(data_links) == 1, 'Should have 1 subsetted and reformatted output file'

    # All output files should have the correct processing tag.
    assert all(
        link['href'].endswith('_subsetted_reformatted.zip') for link in data_links
    ), 'Data link is not .zip file'
