# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Location-based routing with `[[locations]]` configuration blocks in TOML
- `ProxyHandler` for reverse proxying requests to upstream Gemini servers
- Support for multiple handler types per server (static, proxy)
- `strip_prefix` option for proxy locations to remove matched prefix before forwarding
- Configurable timeout for proxy requests (default: 30 seconds)
- `LocationConfig` class for managing location-based handler configuration

### Changed
- Server now supports multiple handlers through location-based routing instead of single handler
- Configuration examples updated to demonstrate location-based routing patterns

## [0.7.0] - 2025-01-XX

### Added
- Titan protocol support for file uploads
- Binary content support for client protocol
- Titan configuration section in config.example.toml

## [0.6.0] - 2025-01-XX

### Added
- Binary content support for client protocol

## [0.5.1] - 2025-01-XX

### Fixed
- Various bug fixes and improvements

[Unreleased]: https://github.com/alanbato/nauyaca/compare/v0.7.0...HEAD
[0.7.0]: https://github.com/alanbato/nauyaca/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/alanbato/nauyaca/compare/v0.5.1...v0.6.0
[0.5.1]: https://github.com/alanbato/nauyaca/releases/tag/v0.5.1
