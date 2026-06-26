import math
import time
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import app, lifespan
from app.config import Settings


class TestAppMain(IsolatedAsyncioTestCase):
    def setUp(self):
        super().setUp()
        app.state.settings = Settings(
            port=8080, max_payload_size=5242880, start_time=time.time()
        )

    def tearDown(self):
        if hasattr(app.state, "settings"):
            delattr(app.state, "settings")
        super().tearDown()

    async def test_lifespan_initialization(self):
        """Test ASGI lifespan context manager correctly initializes settings."""
        test_app = FastAPI(lifespan=lifespan)
        async with lifespan(test_app):
            self.assertTrue(hasattr(test_app.state, "settings"))
            self.assertIsInstance(test_app.state.settings, Settings)
            self.assertGreater(test_app.state.settings.start_time, 0.0)

    def test_health_check_endpoint_exact_time(self):
        """Test health check route yields exact expected JSON and status."""
        with patch("time.time") as mock_time:
            mock_time.return_value = 1000.0
            with TestClient(app) as client:
                client.app.state.settings.start_time = 1000.0 - 15.5

                response = client.get("/health")
                self.assertEqual(response.status_code, 200)
                self.assertTrue(
                    response.headers["content-type"].startswith("application/json")
                )
                data = response.json()
                self.assertEqual(data["status"], "healthy")
                self.assertTrue(math.isclose(data["uptime_seconds"], 15.5))

    def test_health_check_endpoint_various_uptimes(self):
        """Test health check under different start times with standard BVA patterns."""
        with patch("time.time") as mock_time:
            mock_time.return_value = 5000.0
            cases = [
                (0.0, 5000.0),
                (1.0, 4999.0),
                (1234.5, 3765.5),
                (5000.0, 0.0),
            ]
            with TestClient(app) as client:
                for offset, expected_uptime in cases:
                    with self.subTest(offset=offset):
                        client.app.state.settings.start_time = 5000.0 - offset
                        response = client.get("/health")
                        self.assertEqual(response.status_code, 200)
                        data = response.json()
                        self.assertEqual(data["status"], "healthy")
                        self.assertTrue(math.isclose(data["uptime_seconds"], offset))

    def test_echo_payload_size_boundary_values(self):
        """BVA tests on max_payload_size dynamic configuration."""
        limit = 15
        cases = [
            ("", True),
            ("a" * (limit - 1), True),
            ("a" * limit, True),
            ("a" * (limit + 1), False),
            ("a" * (limit + 100), False),
        ]

        with TestClient(app) as client:
            client.app.state.settings.max_payload_size = limit
            for body_content, should_succeed in cases:
                with self.subTest(
                    body_len=len(body_content), should_succeed=should_succeed
                ):
                    response = client.post("/echo", content=body_content)
                    if should_succeed:
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response.json()["body"], body_content)
                    else:
                        self.assertEqual(response.status_code, 413)

    def test_echo_default_payload_limit_abort(self):
        """Test POST /echo with Content-Length exceeding default size (5242880)."""
        with TestClient(app) as client:
            client.app.state.settings.max_payload_size = 5242880
            response = client.post(
                "/echo", headers={"Content-Length": "5242881"}, content=""
            )
            self.assertEqual(response.status_code, 413)

    def test_echo_chunked_stream_limit_abort(self):
        """Test chunked transmission that exceeds memory limit midway."""

        def chunk_generator():
            yield b"a" * 15
            yield b"b" * 10

        with TestClient(app) as client:
            client.app.state.settings.max_payload_size = 20
            response = client.post("/echo", content=chunk_generator())
            self.assertEqual(response.status_code, 413)

    def test_content_length_header_parsing(self):
        """Verify Content-Length parsing conforms to strict non-negative integer boundaries."""
        cases = [
            ("-1", 400),
            ("-5000", 400),
            ("abc", 400),
            ("12.34", 400),
            ("True", 400),
            ("False", 400),
        ]
        with TestClient(app) as client:
            for val, expected_status in cases:
                with self.subTest(header_val=val):
                    response = client.post(
                        "/echo", headers={"Content-Length": val}, content="xyz"
                    )
                    self.assertEqual(response.status_code, expected_status)

    def test_x_echo_status_header_validation(self):
        """Validate strict integer conversion and range checking of X-Echo-Status."""
        cases = [
            ("100", 100),
            ("201", 201),
            ("404", 404),
            ("599", 599),
            ("99", 400),
            ("600", 400),
            ("0", 400),
            ("-200", 400),
            ("invalid_value", 400),
            ("True", 400),
            ("False", 400),
            ("200.5", 400),
            ("", 400),
        ]
        with TestClient(app) as client:
            for status_header, expected_status in cases:
                with self.subTest(status_header=status_header):
                    response = client.get(
                        "/echo", headers={"X-Echo-Status": status_header}
                    )
                    self.assertEqual(response.status_code, expected_status)
                    if expected_status == 404:
                        data = response.json()
                        self.assertIn("headers", data)
                        self.assertIn("query_params", data)

    def test_query_parameters_precise_typing(self):
        """Query parameter mapping must distinguish single, multiple, or missing values precisely."""
        cases = [
            ("?a=1", {"a": "1"}),
            ("?a=1&b=", {"a": "1", "b": ""}),
            ("?a=1&b=&a=2", {"a": ["1", "2"], "b": ""}),
            ("?a=", {"a": ""}),
            ("?a=1&a=2&a=3", {"a": ["1", "2", "3"]}),
            ("?a=1&b=2", {"a": "1", "b": "2"}),
            ("", {}),
            ("?", {}),
            ("?param=hello%20world", {"param": "hello world"}),
        ]
        with TestClient(app) as client:
            for query_str, expected in cases:
                with self.subTest(query_str=query_str):
                    response = client.get(f"/echo{query_str}")
                    self.assertEqual(response.status_code, 200)
                    data = response.json()
                    self.assertEqual(data["query_params"], expected)

    def test_echo_http_methods(self):
        """Test GET, POST, PUT, PATCH, DELETE are processed cleanly with mirrored state."""
        methods = ["GET", "POST", "PUT", "PATCH", "DELETE"]
        with TestClient(app) as client:
            for method in methods:
                with self.subTest(method=method):
                    headers = {"X-Custom-Val": "test", "Content-Type": "text/plain"}
                    body_content = "some body text" if method != "GET" else ""

                    response = client.request(
                        method, "/echo", headers=headers, content=body_content
                    )
                    self.assertEqual(response.status_code, 200)

                    data = response.json()
                    self.assertEqual(data["method"], method)

                    mirrored_headers = {
                        k.lower(): v for k, v in data["headers"].items()
                    }
                    self.assertEqual(mirrored_headers.get("x-custom-val"), "test")

                    if body_content:
                        self.assertEqual(data["body"], body_content)
                    else:
                        self.assertIn(data["body"], (None, ""))
