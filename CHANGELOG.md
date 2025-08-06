# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-08-06

### Fixed
- ChromeDriver compatibility issues with Chrome 138.x
- macOS launchd service configuration (plist files)
- Python environment path mismatches
- Script path references in automated execution

### Changed
- Replaced ELYZA LLM with fallback mechanism due to compilation issues
- Updated requirements.txt with version constraints
- Improved error handling and logging throughout the application
- Enhanced progress visibility during Selenium operations

### Added
- Detailed logging for each step of the LINE WORKS posting process
- Comprehensive troubleshooting section in README
- Service management commands documentation
- Automatic log rotation and error tracking

### Removed
- Direct dependency on llama-cpp-python (temporarily)
- Unused model loading code

## [1.0.0] - 2024-XX-XX

### Added
- Initial release with ELYZA LLM integration
- Selenium-based LINE WORKS automation
- Credo content generation and posting
- Basic scheduling with macOS launchd
- Environment variable configuration