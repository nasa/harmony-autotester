"""pytest suite for Harmony net2cog converter."""

from harmony import Collection

from tests.conftest import AutotesterRequest


def test_net2cog(failed_tests, harmony_client, service_collection):
    """Run a request against net2cog and make sure it is successful.

    As a lightweight example, this test will check the Harmony request
    returned a successful status and the output STAC contains only expected
    files. No outputs will be downloaded for further verification to minimise
    overall runtime of the test suite.

    Test fixtures are retrieved from `tests/conftest.py`, which contains
    fixtures common to all Harmony services under test.

    """
    harmony_request = AutotesterRequest(
        collection=Collection(id=service_collection['concept_id']),
        max_results=1,
        format='image/tiff',
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
    """Helper function to check available data links in Harmony results JSON.

    Will ensure:

    * At least one "data" file is included in the output STAC.
    * Every output file has the expected file suffix: `_reformatted.tif`.

    """
    data_links = [link for link in harmony_result_json_links if link['rel'] == 'data']
    assert len(data_links) > 1, 'Should have at least 1 COG output'

    # All output files should have the correct suffix and extension.
    assert all(data_link.endswith('_reformatted.tif') for data_link in data_links), (
        'Not all data links are GeoTIFFs'
    )
