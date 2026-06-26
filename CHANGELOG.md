# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project scaffolding and dependency specifications in `requirements.txt`.
- Environment-driven configuration setup in `app/config.py` with support for `PORT` and `MAX_PAYLOAD_SIZE` variables.
- Standard ASGI entry point and FastAPI application lifecycle management in `app/main.py` using `lifespan`.
- Basic `/health` checking and `/echo` request mirroring routes.
- Base repository `.gitignore` configuration.