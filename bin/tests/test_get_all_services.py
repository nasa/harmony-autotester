"""Offline regression tests for CMR discovery pagination and retry exhaustion."""

import importlib.util
import json
import os
import runpy
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import requests

SCRIPT = Path(__file__).resolve().parents[1] / 'get_all_services.py'
SPEC = importlib.util.spec_from_file_location('get_all_services', SCRIPT)
discovery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(discovery)

URL = 'https://cmr.example.invalid/graphql'
COLLECTION = {'conceptId': 'C1-TEST', 'shortName': 'example', 'version': '1'}
SERVICE = {
    'conceptId': 'S1-TEST',
    'name': 'Example service',
    'version': '1',
    'collections': {'count': 1},
}


def page(kind, items, cursor=None):
    """Build a discovery response with the real GraphQL result structure."""
    content = {'items': deepcopy(items), 'cursor': cursor}
    if kind == 'collections':
        return {'data': {'service': {'collections': content}}}
    return {'data': {'services': content}}


class DiscoveryTests(unittest.TestCase):
    """Drive real Requests sessions at an intercepted transport boundary."""

    def setUp(self):
        """Ensure every outbound request is intercepted and explicitly queued."""
        self.responses = []
        self.requests = []
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers['Authorization'] = 'Bearer synthetic-test-token'
        self.addCleanup(self.session.close)
        send = patch.object(
            requests.Session, 'send', autospec=True, side_effect=self.send
        )
        send.start()
        self.addCleanup(send.stop)

    def send(self, session, request, **kwargs):
        """Return queued real Responses without opening a network connection."""
        self.requests.append((request, kwargs))
        if not self.responses:
            self.fail(f'Unexpected request: {request.method} {request.url}')
        queued = self.responses.pop(0)
        if isinstance(queued, Exception):
            raise queued
        status, content = queued
        response = requests.Response()
        response.status_code = status
        response.url = request.url
        response.request = request
        response.headers['Content-Type'] = 'application/json'
        response._content = json.dumps(content).encode('utf-8')
        return response

    def query(self, kind):
        """Call the real discovery function under test."""
        if kind == 'collections':
            return discovery.get_service_collections(self.session, URL, 'S1-TEST')
        return discovery.get_all_harmony_services(self.session, URL)

    def reset_requests(self):
        """Reset the isolated transport queue between subcases."""
        self.requests.clear()
        self.responses.clear()

    def test_first_page_exhaustion_raises_http_error(self):
        """A permanently failed first page must not become an empty result."""
        for kind in ('services', 'collections'):
            for status in (401, 429, 503):
                with self.subTest(kind=kind, status=status):
                    self.reset_requests()
                    self.responses = [(status, {'error': 'unavailable'})] * 3
                    with self.assertRaises(requests.HTTPError) as error:
                        self.query(kind)
                    self.assertEqual(error.exception.response.status_code, status)
                    self.assertEqual(error.exception.request.url, URL)
                    self.assertEqual(len(self.requests), 3)
                    self.assertFalse(self.responses)

    def test_later_page_exhaustion_does_not_return_partial_data(self):
        """Successful earlier pages cannot hide an exhausted later page."""
        for kind, item in (('services', SERVICE), ('collections', COLLECTION)):
            with self.subTest(kind=kind):
                self.reset_requests()
                self.responses = [(200, page(kind, [item], 'page-two'))]
                self.responses += [(503, {'error': 'unavailable'})] * 3
                # The original service path continues into nested discovery.
                if kind == 'services':
                    self.responses.append((200, page('collections', [COLLECTION])))
                with self.assertRaises(requests.HTTPError):
                    self.query(kind)
                self.assertEqual(len(self.requests), 4)
                parameters = kind + 'Params'
                cursors = [
                    json.loads(r.body)['variables'][parameters].get('cursor')
                    for r, _ in self.requests
                ]
                self.assertEqual(cursors, [None, 'page-two', 'page-two', 'page-two'])

    def test_recovery_keeps_the_cursor_and_does_not_duplicate_items(self):
        """Two transient failures retain the existing retry and ordering rules."""
        for kind, item in (('services', SERVICE), ('collections', COLLECTION)):
            with self.subTest(kind=kind):
                self.reset_requests()
                self.responses = [
                    (503, {}),
                    (200, page(kind, [item], 'next')),
                    (502, {}),
                    (200, page(kind, [], None)),
                ]
                if kind == 'services':
                    self.responses.append((200, page('collections', [COLLECTION])))
                result = self.query(kind)
                self.assertEqual(len(result), 1)
                self.assertEqual(result[0]['concept_id'], item['conceptId'])
                self.assertFalse(self.responses)
                key = kind + 'Params'
                self.assertEqual(
                    [
                        json.loads(r.body)['variables'][key].get('cursor')
                        for r, _ in self.requests[:4]
                    ],
                    [None, None, 'next', 'next'],
                )
                for request, kwargs in self.requests:
                    self.assertEqual(
                        request.headers['Authorization'], 'Bearer synthetic-test-token'
                    )
                    self.assertEqual(kwargs['timeout'], 10)

    def test_error_budget_is_still_cumulative_across_pages(self):
        """A successful page does not reset the existing three-error budget."""
        self.responses = [
            (500, {}),
            (200, page('collections', [COLLECTION], 'next')),
            (502, {}),
            (200, page('collections', [], 'last')),
            (503, {}),
        ]
        with self.assertRaises(requests.HTTPError) as error:
            self.query('collections')
        self.assertEqual(error.exception.response.status_code, 503)
        self.assertEqual(len(self.requests), 5)

    def test_nested_collection_failure_propagates_through_service_discovery(self):
        """A discovered service must not contain an incomplete collection list."""
        self.responses = [
            (200, page('services', [SERVICE])),
            (200, page('collections', [COLLECTION], 'next')),
            (503, {}),
            (503, {}),
            (503, {}),
        ]
        with self.assertRaises(requests.HTTPError):
            self.query('services')
        self.assertEqual(len(self.requests), 5)

    def test_empty_results_remain_successful(self):
        """A successful, genuinely empty discovery response remains empty."""
        for kind in ('services', 'collections'):
            with self.subTest(kind=kind):
                self.reset_requests()
                self.responses = [(200, page(kind, []))]
                self.assertEqual(self.query(kind), [])
                self.assertEqual(len(self.requests), 1)

    def test_collection_order_and_fields_are_preserved(self):
        """Multi-page responses retain all normalized metadata in service order."""
        second = {**COLLECTION, 'conceptId': 'C2-TEST', 'version': '2'}
        self.responses = [
            (200, page('services', [SERVICE])),
            (200, page('collections', [COLLECTION], 'next')),
            (200, page('collections', [second])),
        ]
        self.assertEqual(
            self.query('services'),
            [
                {
                    'concept_id': 'S1-TEST',
                    'name': 'Example service',
                    'version': '1',
                    'collection_count': 1,
                    'collections': [
                        {
                            'concept_id': 'C1-TEST',
                            'short_name': 'example',
                            'version': '1',
                        },
                        {
                            'concept_id': 'C2-TEST',
                            'short_name': 'example',
                            'version': '2',
                        },
                    ],
                }
            ],
        )
        self.assertFalse(self.responses)

    def test_transport_exceptions_remain_unmodified(self):
        """Timeouts and connection errors retain their existing immediate failure."""
        for kind in ('services', 'collections'):
            for error_type in (requests.Timeout, requests.ConnectionError):
                with self.subTest(kind=kind, error=error_type):
                    self.reset_requests()
                    error = error_type('synthetic transport failure')
                    self.responses = [error]
                    with self.assertRaises(error_type) as raised:
                        self.query(kind)
                    self.assertIs(raised.exception, error)
                    self.assertEqual(len(self.requests), 1)

    def test_successful_entry_point_publishes_complete_matrix(self):
        """Successful CLI discovery still appends its result to workflow output."""
        self.responses = [
            (200, [{'access_token': 'synthetic-test-token'}]),
            (200, page('services', [SERVICE])),
            (200, page('collections', [COLLECTION])),
        ]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'github-output'
            output.write_text('previous=value\n', encoding='utf-8')
            environment = {
                'CMR_GRAPHQL_URL': URL,
                'EARTHDATA_URL': 'https://auth.example.invalid',
                'EARTHDATA_USERNAME': 'test-user',
                'EARTHDATA_PASSWORD': 'test-only',
                'GITHUB_OUTPUT': str(output),
            }
            with patch.dict(os.environ, environment):
                runpy.run_path(str(SCRIPT), run_name='__main__')
            lines = output.read_text(encoding='utf-8').splitlines()
            self.assertEqual(lines[0], 'previous=value')
            result = json.loads(lines[1].removeprefix('all_services='))
            self.assertEqual(result[0]['concept_id'], 'S1-TEST')
            self.assertEqual(result[0]['collections'][0]['concept_id'], 'C1-TEST')
        self.assertFalse(self.responses)

    def test_failed_entry_point_does_not_publish_a_partial_matrix(self):
        """The workflow output stays untouched when discovery cannot finish."""
        self.responses = [
            (200, [{'access_token': 'synthetic-test-token'}]),
            (200, page('services', [SERVICE], 'next')),
            (503, {}),
            (503, {}),
            (503, {}),
            (200, page('collections', [COLLECTION])),
        ]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'github-output'
            output.write_text('previous=value\n', encoding='utf-8')
            environment = {
                'CMR_GRAPHQL_URL': URL,
                'EARTHDATA_URL': 'https://auth.example.invalid',
                'EARTHDATA_USERNAME': 'test-user',
                'EARTHDATA_PASSWORD': 'test-only',
                'GITHUB_OUTPUT': str(output),
            }
            with patch.dict(os.environ, environment):
                with self.assertRaises(requests.HTTPError):
                    runpy.run_path(str(SCRIPT), run_name='__main__')
            self.assertEqual(output.read_text(encoding='utf-8'), 'previous=value\n')
        self.assertEqual(len(self.requests), 5)


if __name__ == '__main__':
    unittest.main()
