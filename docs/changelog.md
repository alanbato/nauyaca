# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Documentation now hosted on Read the Docs

## [0.2.0] - 2025-01-XX

### Added
- Full Gemini protocol server implementation with asyncio Protocol/Transport pattern
- Full Gemini protocol client implementation with asyncio support
- TOFU (Trust-On-First-Use) certificate validation for secure connections
- SQLite-backed TOFU database with fingerprint storage and verification
- Certificate generation, fingerprinting, and validation utilities
- Rate limiting using token bucket algorithm with per-IP tracking
- IP-based access control with allow/deny lists supporting CIDR notation
- Middleware chain architecture for composable request processing
- Client certificate authentication support (status codes 60-62)
- Path-based client certificate requirements with pattern matching
- TOML configuration file support for server settings
- CLI command: `nauyaca serve` - start Gemini server
- CLI command: `nauyaca get` - fetch Gemini resources
- CLI command: `nauyaca cert` - generate and manage certificates
- CLI command: `nauyaca tofu` - manage TOFU database (list, trust, revoke, export, import)
- Privacy-preserving IP hashing in server logs using SHA-256
- Comprehensive status code support (1x through 6x ranges)
- Request timeout protection (30 second default)
- Request size validation (1024 byte limit per Gemini spec)
- Path traversal protection with secure path resolution
- TLS 1.2+ enforcement for all connections
- Structured logging with contextual information
- Rich terminal output with progress indicators

### Changed
- Minimum Python version lowered to 3.10 (from 3.11)
- CLI command renamed from `nauyaca fetch` to `nauyaca get` for consistency
- Improved URL validation to reject userinfo and fragment components
- Client enforces trailing slash on empty paths for consistency

### Fixed
- TOFU implementation now correctly stores and validates certificates
- Middleware handlers properly chain and execute in correct order
- URL parsing correctly handles edge cases per Gemini specification

### Security
- Certificate fingerprint verification prevents MITM attacks
- Rate limiting prevents denial-of-service attacks (status 44: SLOW DOWN)
- Path canonicalization prevents directory traversal attacks
- Request size limits prevent memory exhaustion
- TLS minimum version enforcement ensures secure connections
- Client certificate validation for authenticated access

## [0.1.0] - 2024-12-XX

### Added
- Initial project structure and basic implementation
- Core protocol request/response handling
- Basic server and client functionality
- TLS certificate support

[Unreleased]: https://github.com/alanbato/nauyaca/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/alanbato/nauyaca/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/alanbato/nauyaca/releases/tag/v0.1.0
