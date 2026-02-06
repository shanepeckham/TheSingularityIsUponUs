# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-02-06

### Added
- Initial release of Release Flow Framework
- Automated code improvement using GitHub Copilot SDK
- PR workflow with automatic branch creation, commits, and pull requests
- CI integration with configurable waiting for checks
- Continuous mode for multiple improvement iterations
- Highly configurable via dataclasses
- Command-line interface
- Python API for programmatic usage
- Callback system for custom integrations
- Comprehensive error handling and logging
- Type hints for better IDE support and type safety
- Input validation in configuration
- Proper exception handling throughout codebase
- MIT License
- Comprehensive documentation

### Changed
- Replaced print statements with proper logging module
- Added constants for magic numbers
- Improved error messages and debugging information
- Enhanced async/await consistency

### Security
- Added timeout to GitHub CLI token retrieval
- Better handling of GitHub tokens and credentials
- Input validation for repository names and configuration
