import time
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from fastapi import FastAPI, Request, HTTPException
from fastapi.testclient import TestClient

from app.main import app, health_check, echo_handler, lifespan
from app.config import Settings


class TestMainModule(IsolatedAsyncioTestCase):
    def setUp(self):
        super().setUp()
        # Reset app.state.settings before every test to ensure strict state isolation
        app.state.settings = Settings(
            port=8080, max_payload_size=5242880, start_time=time.time()
        )

    def tearDown(self):
        if hasattr(app.state, "settings"):
            delattr(app.state, "settings")
        super().tearDown()

    async def test_lifespan(self):
        """Test that the lifespan context manager properly initializes app settings."""
        test_app = FastAPI(lifespan=lifespan)
        async with lifespan(test_app):
            self.assertTrue(hasattr(test_app.state, "settings"))
            self.assertIsInstance(test_app.state.settings, Settings)
            self.assertGreater(test_app.state.settings.start_time, 0.0)

    async def test_health_check_direct(self):
        """Test direct call to health_check function under various start times."""
        now = time.time()
        for start_time_offset in [0.0, 10.0, 100.0, 1e5]:
            with self.subTest(offset=start_time_offset):
                app.state.settings.start_time = now - start_time_offset
                res = await health_check()
                self.assertIsInstance(res, dict)
                self.assertEqual(res["status"], "ok")
                self.assertGreaterEqual(res["uptime"], start_time_offset)

    def test_health_check_endpoint(self):
        """Test health check route via TestClient."""
        with TestClient(app) as client:
            response = client.get("/health")
            self.assertEqual(response.status_code, 200)
            self.assertTrue(
                response.headers["content-type"].startswith("application/json")
            )
            data = response.json()
            self.assertEqual(data["status"], "ok")
            self.assertIsInstance(data["uptime"], (int, float))

    async def test_echo_handler_direct_parametrized(self):
        """Test echo_handler directly with various query strings, headers, and payloads."""
        app.state.settings.max_payload_size = 1000

        cases = [
            (
                [(b"x-custom-header", b"custom_val")],
                b"param1=hello&param2=world",
                b'{"key": "value"}',
            ),
            ([(b"user-agent", b"tester")], b"flag=true", b"plain text payload"),
            ([], b"", b""),
            (
                [(b"content-type", b"application/json"), (b"accept", b"*/*")],
                b"a=1&b=2",
                b"payload_content",
            ),
        ]

        for headers, query_string, body_bytes in cases:
            with self.subTest(
                headers=headers, query_string=query_string, body_bytes=body_bytes
            ):
                scope = {
                    "type": "http",
                    "method": "POST",
                    "path": "/echo",
                    "headers": headers,
                    "query_string": query_string,
                }

                async def mock_receive():
                    return {
                        "type": "http.request",
                        "body": body_bytes,
                        "more_body": False,
                    }

                req = Request(scope, receive=mock_receive)
                res = await echo_handler(req)
                self.assertIsInstance(res, dict)

                res_headers = {k.lower(): v for k, v in res.get("headers", {}).items()}
                for k, v in headers:
                    k_str = k.decode("utf-8").lower()
                    v_str = v.decode("utf-8")
                    self.assertIn(k_str, res_headers)
                    self.assertEqual(res_headers[k_str], v_str)

                expected_body_str = body_bytes.decode("utf-8", errors="replace")
                self.assertEqual(res.get("body"), expected_body_str)
                self.assertIsInstance(res.get("query_params"), dict)

    async def test_echo_handler_payload_limits_direct_bva(self):
        """Boundary Value Analysis for payload limit on direct echo_handler call."""
        limit = 5
        app.state.settings.max_payload_size = limit

        bva_cases = [
            (b"", True),
            (b"a", True),
            (b"a" * (limit - 1), True),
            (b"a" * limit, True),
            (b"a" * (limit + 1), False),
        ]

        for payload, should_pass in bva_cases:
            with self.subTest(payload_len=len(payload), should_pass=should_pass):
                scope = {
                    "type": "http",
                    "method": "POST",
                    "path": "/echo",
                    "headers": [],
                    "query_string": b"",
                }

                async def mock_receive():
                    return {
                        "type": "http.request",
                        "body": payload,
                        "more_body": False,
                    }

                req = Request(scope, receive=mock_receive)

                if should_pass:
                    res = await echo_handler(req)
                    self.assertIsInstance(res, dict)
                    self.assertEqual(res.get("body"), payload.decode("utf-8"))
                else:
                    with self.assertRaises(HTTPException):
                        await echo_handler(req)

    def test_echo_endpoint_payload_limit_client(self):
        """Test payload limits via TestClient with patched settings."""
        patched_settings = Settings(max_payload_size=10)

        with (
            patch("app.main.get_settings", return_value=patched_settings),
            patch("app.config.get_settings", return_value=patched_settings),
        ):
            with TestClient(app) as client:
                response_ok = client.post("/echo", content="1" * 10)
                self.assertEqual(response_ok.status_code, 200)

                response_fail = client.post("/echo", content="1" * 11)
                self.assertEqual(response_fail.status_code, 413)

    def test_echo_endpoint_integration(self):
        """General integration test of the /echo endpoint using TestClient."""
        with TestClient(app) as client:
            headers = {"X-Test-Header": "IntegrationTest", "Accept": "application/json"}
            params = {"foo": "bar", "baz": "qux"}
            payload = "Hello World!"

            response = client.post(
                "/echo", headers=headers, params=params, content=payload
            )

            self.assertEqual(response.status_code, 200)
            self.assertTrue(
                response.headers["content-type"].startswith("application/json")
            )

            data = response.json()
            self.assertEqual(data["body"], payload)

            echoed_headers = {k.lower(): v for k, v in data["headers"].items()}
            self.assertIn("x-test-header", echoed_headers)
            self.assertEqual(echoed_headers["x-test-header"], "IntegrationTest")

            echoed_params = data["query_params"]
            self.assertEqual(echoed_params.get("foo"), "bar")
            self.assertEqual(echoed_params.get("baz"), "qux")
