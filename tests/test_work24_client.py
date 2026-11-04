import urllib.error
import urllib.parse
import unittest

from src.ingestion.work24_client import (
    WORK24_LIST_URL,
    Work24ApiError,
    Work24Client,
)


FAKE_XML = b"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<wantedRoot>
  <total>1</total><startPage>1</startPage><display>10</display>
  <wanted><wantedAuthNo>TEST-001</wantedAuthNo><company>Example Co</company>
    <title>Software Engineer</title><region>Busan</region><regDt>2025-01-02</regDt>
    <wantedInfoUrl>https://example.invalid/job</wantedInfoUrl><jobsCd>1234</jobsCd>
  </wanted>
</wantedRoot>"""


class FakeResponse:
    status = 200

    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit):
        return self.body


class Work24ClientTests(unittest.TestCase):
    def test_list_request_and_xml_parsing_use_mock_transport(self):
        captured = {}

        def fake_open(request, timeout):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            return FakeResponse(FAKE_XML)

        client = Work24Client("test-secret-not-real", opener=fake_open)
        result = client.list_jobs(
            start_page=2,
            display=5,
            filters={"region": "TEST_REGION", "occupation": "100|200"},
        )
        query = urllib.parse.parse_qs(urllib.parse.urlparse(captured["url"]).query)
        self.assertEqual(WORK24_LIST_URL, urllib.parse.urlunparse(urllib.parse.urlparse(captured["url"])._replace(query="", fragment="")))
        self.assertEqual(["test-secret-not-real"], query["authKey"])
        self.assertEqual(["L"], query["callTp"])
        self.assertEqual(["XML"], query["returnType"])
        self.assertEqual(["2"], query["startPage"])
        self.assertEqual(["5"], query["display"])
        self.assertEqual(["100|200"], query["occupation"])
        self.assertEqual(10.0, captured["timeout"])
        self.assertEqual(1, result.total)
        self.assertEqual("TEST-001", result.jobs[0]["wantedAuthNo"])
        self.assertEqual("Software Engineer", result.jobs[0]["title"])
        self.assertEqual("Busan", result.jobs[0]["region"])

    def test_paging_and_filter_validation_fail_before_network(self):
        def fail_if_called(*_args, **_kwargs):
            self.fail("network opener must not run for invalid input")

        client = Work24Client("fake", opener=fail_if_called)
        with self.assertRaises(ValueError):
            client.list_jobs(display=101)
        with self.assertRaises(ValueError):
            client.list_jobs(start_page=1001)
        with self.assertRaises(ValueError):
            client.list_jobs(filters={"notAFilter": "x"})
        with self.assertRaises(ValueError):
            client.list_jobs(filters={"salTp": "Y"})
        with self.assertRaises(ValueError):
            client.list_jobs(filters={"career": "E"})

    def test_transport_exception_does_not_echo_possible_secret(self):
        secret = "fake-secret-not-real"

        def failed_open(*_args, **_kwargs):
            raise urllib.error.URLError(f"request contained {secret}")

        client = Work24Client(secret, opener=failed_open)
        with self.assertRaises(Work24ApiError) as caught:
            client.list_jobs()
        self.assertNotIn(secret, str(caught.exception))

    def test_malformed_xml_fails_closed_without_echoing_body(self):
        with self.assertRaises(Work24ApiError):
            Work24Client._parse_xml(b"<private>response detail</private>")


if __name__ == "__main__":
    unittest.main()
