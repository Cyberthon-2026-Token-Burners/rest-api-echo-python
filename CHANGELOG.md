# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Core dynamic ASGI lifespan setup to capture start timestamp on launch (`app.state.settings.start_time`).
- Implement `/health` dynamic liveness response showing uptime calculations.
- Stateless `/echo` multi-method route supporting `GET`, `POST`, `PUT`, `PATCH`, and `DELETE` requests.
- Robust `Content-Length` header check and real-time chunk streaming boundaries to strictly reject payloads above 5.0 MB (5,242,880 bytes) with `413 Payload Too Large`.
- Custom status mocking support via header validation of `X-Echo-Status` (returning HTTP 400 for bad values).
- Advanced query parameter parser implementing precise string, empty-string, and array-mapping rules.
- Defensive input parameter handling for negative sizes, integer conversions, and invalid boolean keywords.