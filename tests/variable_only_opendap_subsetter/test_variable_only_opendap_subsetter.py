"""pytest suite for the variable-only-opendap-subsetter service chain."""

import earthaccess
from harmony import Collection

from tests.conftest import AutotesterRequest, get_configured_variable_names

NETCDF4_FORMAT = 'application/netcdf'
OPENDAP_URL_FORMAT = 'application/x-netcdf4;profile=opendap_url'


def test_variable_only_opendap_subsetter(
    failed_tests, harmony_client, service_collection, earthaccess_login
):
    """Run a variable subset request for variable-only-opendap-subsetter."""
    try:
        harmony_request = None

        granules = earthaccess.search_data(
            collection_concept_id=service_collection['concept_id'], count=1
        )
        assert granules, 'The collection has no granules'

        # Request up to two configured variables (all variables if none are configured).
        variables = get_configured_variable_names(
            harmony_client, service_collection['concept_id']
        )[0:2]
        # In this test, a request for all variables in netcdf format won't result in a
        # variable subset request; Harmony routes it to harmony/download, which is
        # listed before this chain. For all variables, ask for OPENDAP URL which is
        # also supported by the chain.
        output_format = OPENDAP_URL_FORMAT if variables == ['all'] else NETCDF4_FORMAT

        harmony_request = AutotesterRequest(
            collection=Collection(id=service_collection['concept_id']),
            granule_id=[granules[0]['meta']['concept-id']],
            variables=variables,
            format=output_format,
        )

        # Submit the job and get the JSON output once completed
        harmony_job_id = harmony_client.submit(harmony_request)
        result_json = harmony_client.result_json(harmony_job_id)

        # Check the response was successful
        assert result_json['status'] == 'successful', (
            f'Harmony request failed:\n\n{result_json["message"]}'
        )

        # Check the result is a subsetted file, or an OPeNDAP request URL.
        ensure_correct_output(
            result_json['links'], output_format, result_json['message']
        )
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


def ensure_correct_output(
    harmony_result_json_links: list[dict], output_format: str, message: str
):
    """Check the output link.

    For NetCDF-4 output, HOSS stages one file with the HOSS subsetting suffix
    `_subsetted.nc4`. For OPeNDAP URL output, HOSS returns the unexecuted
    OPeNDAP request URL instead: a DAP4 request for the `.dap.nc4` response of
    the granule, with the variables in a `dap4.ce` constraint expression.

    """
    data_links = [link for link in harmony_result_json_links if link['rel'] == 'data']
    assert len(data_links) == 1, (
        f'Expected 1 data link, but found {len(data_links)}:\n\n{message}'
    )

    if output_format == OPENDAP_URL_FORMAT:
        assert '.dap.nc4?dap4.ce=' in data_links[0]['href'], (
            f'Data link is not an OPeNDAP DAP4 request URL:\n\n{data_links[0]["href"]}'
        )
    else:
        assert data_links[0]['href'].endswith('_subsetted.nc4'), (
            f'Data link is not a subsetted NetCDF-4 file:\n\n{data_links[0]["href"]}'
        )
