import os
import unittest
from unittest.mock import patch
import math
from app.config import Settings, get_settings


class TestConfig(unittest.TestCase):
    def test_settings_defaults(self):
        settings = Settings()
        self.assertEqual(settings.port, 8080)
        self.assertEqual(settings.max_payload_size, 5242880)
        self.assertEqual(settings.start_time, 0.0)

    def test_settings_custom_values(self):
        settings = Settings(port=9090, max_payload_size=1024, start_time=123.45)
        self.assertEqual(settings.port, 9090)
        self.assertEqual(settings.max_payload_size, 1024)
        self.assertTrue(math.isclose(settings.start_time, 123.45))

    def test_settings_float_boundaries(self):
        settings = Settings(start_time=math.pi)
        self.assertTrue(
            math.isclose(settings.start_time, 3.141592653589793, rel_tol=1e-9)
        )
        settings_inf = Settings(start_time=float("inf"))
        self.assertEqual(settings_inf.start_time, float("inf"))

    def test_settings_invalid_types(self):
        type_cases = [
            {"port": True},
            {"port": False},
            {"port": 80.5},
            {"port": "8080"},
            {"max_payload_size": True},
            {"max_payload_size": False},
            {"max_payload_size": 1024.5},
            {"max_payload_size": "5242880"},
            {"start_time": 123},
            {"start_time": "123.45"},
        ]
        for case in type_cases:
            with self.subTest(case=case):
                with self.assertRaises(TypeError):
                    Settings(**case)

    @patch.dict(os.environ, {}, clear=True)
    def test_get_settings_defaults(self):
        settings = get_settings()
        self.assertEqual(settings.port, 8080)
        self.assertEqual(settings.max_payload_size, 5242880)

    def test_get_settings_valid_env(self):
        test_cases = [
            ({"PORT": "9090"}, 9090, 5242880),
            ({"MAX_PAYLOAD_SIZE": "1048576"}, 8080, 1048576),
            ({"PORT": "80", "MAX_PAYLOAD_SIZE": "100"}, 80, 100),
            ({"PORT": "1"}, 1, 5242880),
            ({"MAX_PAYLOAD_SIZE": "1"}, 8080, 1),
            ({"PORT": "2147483647"}, 2147483647, 5242880),
        ]
        for env, expected_port, expected_size in test_cases:
            with self.subTest(env=env):
                with patch.dict(os.environ, env, clear=True):
                    settings = get_settings()
                    self.assertEqual(settings.port, expected_port)
                    self.assertEqual(settings.max_payload_size, expected_size)

    def test_get_settings_invalid_env(self):
        invalid_envs = [
            {"PORT": "abc"},
            {"MAX_PAYLOAD_SIZE": "xyz"},
            {"PORT": "abc", "MAX_PAYLOAD_SIZE": "xyz"},
            {"PORT": "80.5"},
            {"MAX_PAYLOAD_SIZE": "1024.0"},
            {"PORT": "0"},
            {"MAX_PAYLOAD_SIZE": "0"},
            {"PORT": "-80"},
            {"MAX_PAYLOAD_SIZE": "-100"},
            {"PORT": ""},
            {"MAX_PAYLOAD_SIZE": ""},
            {"PORT": "True"},
            {"PORT": "False"},
            {"PORT": "true"},
            {"PORT": "false"},
            {"PORT": "   "},
            {"MAX_PAYLOAD_SIZE": " \\t "},
        ]
        for env in invalid_envs:
            with self.subTest(env=env):
                with patch.dict(os.environ, env, clear=True):
                    with self.assertRaises(ValueError):
                        get_settings()
