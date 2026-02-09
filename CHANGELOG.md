# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive documentation (README, ARCHITECTURE, QUICKSTART, ADRs)
- CI/CD pipeline with GitHub Actions
- Strict mypy configuration with incremental migration plan
- Code quality workflows (weekly reports)

### Changed
- Updated CI workflow to use pyproject.toml instead of requirements-dev.txt
- Improved test coverage reporting

## [0.2.0] - 2026-02-09

### Added
- Clean Architecture refactoring for СветВЛифтах
- Domain-Driven Design patterns
- 59 automated tests with Revit API mocks
- Spatial indexing for deduplication (O(n) performance)
- Batch processing (25× fewer transactions)
- Mojibake tolerance for Russian family names
- Shared Kernel (lib/) with 20+ reusable modules
- Dev tooling: pytest, black, flake8, isort, mypy, pre-commit

### Changed
- Refactored orchestrator layer for better separation of concerns
- Improved error handling and logging

### Fixed
- Encoding issues with Russian text (mojibake)
- Memory leaks in transaction handling
- Performance bottlenecks in element placement

## [0.1.0] - 2024-12-01

### Added
- Initial release
- Basic lighting placement tools
- Socket placement automation
- Panel and switch tools
- Hub command interface

---

## Release Process

1. Update version in `pyproject.toml`
2. Update this `CHANGELOG.md` with new version section
3. Commit changes: `git commit -m "chore: bump version to X.Y.Z"`
4. Create tag: `git tag vX.Y.Z`
5. Push tag: `git push origin vX.Y.Z`
6. GitHub Actions will automatically create release

---

## Categories

- **Added** for new features
- **Changed** for changes in existing functionality
- **Deprecated** for soon-to-be removed features
- **Removed** for now removed features
- **Fixed** for any bug fixes
- **Security** for vulnerability fixes
