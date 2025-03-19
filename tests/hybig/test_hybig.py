"""pytest suite for Harmony Browse Image Generator (HyBIG)."""

from os.path import basename

from harmony import Collection, Request


def test_hybig(failed_tests, harmony_client, service_collection):
    """Run a request against HyBIG and make sure it is successful.

    As a lightweight example, this test will check the Harmony request
    returned a successful status and the output STAC contains all expected
    files. No outputs will be downloaded for further verification to minimise
    overall runtime of the test suite.

    Test fixtures are retrieved from `tests/conftest.py`, which contains
    fixtures common to all Harmony services under test.

    """
    harmony_request = Request(
        collection=Collection(id=service_collection['concept_id']),
        max_results=1,
        format='image/png',
    )

    try:
        # Submit the job and get the JSON output once completed
        harmony_job_id = harmony_client.submit(harmony_request)
        result_json = harmony_client.result_json(harmony_job_id)

        # Check the response was successful
        assert result_json['status'] == 'successful', (
            f'Harmony request failed: {result_json["message"]}'
        )

        # Check the URLs for results are all of the expected type.
        ensure_correct_files_created(result_json['links'])
    except AssertionError as exception:
        # Cache error message and re-raise the AssertionError to fail the test
        failed_tests.append(
            {
                **service_collection,
                'error': str(exception),
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

    * There are at least 3 files.
      * For a granule that is not tiled, that is 1 PNG, 1 world file (.pgw) and
        1 auxiliary file (.aux.xml).
      * For a tiled output, that is 1 text file listing all other files, 1
        PNG per tile, 1 world file per tile (.pgw), and 1 auxiliary file per
        tile (.aux.xml).
    * Every PNG file should have a corresponding world file and auxiliary file,
      with a matching basename (excluding extensions).

    """
    data_links = [link for link in harmony_result_json_links if link['rel'] == 'data']
    assert len(data_links) >= 3, 'Should have at least 1 png, pgw and aux.xml'

    # All tiles (or whole granule) should have a PNG, a world file and
    # an auxiliary file:
    png_files = set(
        basename(link['href']).replace('.png', '')
        for link in data_links
        if link['href'].endswith('.png')
    )

    pgw_files = set(
        basename(link['href']).replace('.pgw', '')
        for link in data_links
        if link['href'].endswith('.pgw')
    )

    aux_xml_files = set(
        basename(link['href']).replace('.png.aux.xml', '')
        for link in data_links
        if link['href'].endswith('.png.aux.xml')
    )

    assert png_files == pgw_files, 'PNG and world file mismatch'
    assert png_files == aux_xml_files, 'PNG and auxiliary file mismatch'
