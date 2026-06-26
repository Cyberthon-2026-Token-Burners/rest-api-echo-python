import os


def _parse_positive_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    # Reject booleans encoded as strings and floats
    if raw.strip().lower() in ("true", "false"):
        raise ValueError(f"{name} must be a strictly positive integer, got {raw!r}")
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"{name} must be a strictly positive integer, got {raw!r}")
    if value <= 0:
        raise ValueError(f"{name} must be strictly positive, got {value}")
    return value


class Settings:
    def __init__(
        self, port: int = 8080, max_payload_size: int = 5242880, start_time: float = 0.0
    ):
        if not (isinstance(port, int) and not isinstance(port, bool)):
            raise TypeError("port must be an int")
        if not (
            isinstance(max_payload_size, int) and not isinstance(max_payload_size, bool)
        ):
            raise TypeError("max_payload_size must be an int")
        if not isinstance(start_time, float):
            raise TypeError("start_time must be a float")
        self.port = port
        self.max_payload_size = max_payload_size
        self.start_time = start_time


def get_settings() -> Settings:
    port = _parse_positive_int("PORT", 8080)
    max_payload_size = _parse_positive_int("MAX_PAYLOAD_SIZE", 5242880)
    return Settings(port=port, max_payload_size=max_payload_size)
