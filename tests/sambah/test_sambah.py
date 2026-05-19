"""pytest suite for Harmony sambah converter."""

from collections import defaultdict

import earthaccess
from batchee.tempo_filename_parser import get_batch_indices
from harmony import BBox, CapabilitiesRequest, Collection

from tests.conftest import AutotesterRequest
from tests.umm_g_utilities import (
    generate_near_full_spatial_box,
    generate_near_full_temporal_range,
    generate_near_full_variable_subset,
    get_granule_filename,
)


def test_sambah(failed_tests, harmony_client, service_collection, earthaccess_login):
    """Run a request against sambah and make sure it is successful.

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
            collection_concept_id=service_collection['concept_id'], count=100
        )
        assert granules, 'The collection has no granules'

        granule_names = [get_granule_filename(granule) for granule in granules]
        batch_indices = get_batch_indices(granule_names)

        grouped = defaultdict(list)

        for k, v in zip(batch_indices, granules, strict=False):
            grouped[k].append(v)

        scans = sorted(grouped.values(), key=len)
        assert scans, 'No compatible scans were found'

        if len(scans) > 1:
            # Select 1 granule from one scan and up to 2 from another scan
            selected_granules = scans[-2][:1] + scans[-1][:2]
        else:
            # Only one scan available; select up to 2 granules
            selected_granules = scans[-1][:2]

        granule_id = [granule['meta']['concept-id'] for granule in selected_granules]

        west, east, south, north = generate_near_full_spatial_box(selected_granules)
        start_time, stop_time = generate_near_full_temporal_range(selected_granules)

        cap_request = CapabilitiesRequest(
            collection_id=service_collection['concept_id']
        )
        capabilities = harmony_client.submit(cap_request)
        selected_variables = generate_near_full_variable_subset(capabilities)

        harmony_request = AutotesterRequest(
            collection=Collection(id=service_collection['concept_id']),
            extend=True,
            concatenate=True,
            spatial=BBox(west, south, east, north),
            temporal={'start': start_time, 'stop': stop_time},
            variables=selected_variables,
            granule_id=granule_id,
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
    assert len(data_links) == 1, 'Should have 1 concatenated output file'

    # All output files should have the correct processing tags.
    processing_tags = ['subsetted', 'stitched', 'merged']
    assert all(
        all(tag in link['href'] for tag in processing_tags) for link in data_links
    ), 'Not all data links contain all processing tags'
