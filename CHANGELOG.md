 # Changelog
 
 All notable changes to this project will be documented in this file.
 
 The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
 and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
 
 ## [Unreleased]
 
 ### Added
 - Nothing yet
 
 ## [0.2.0] - 2026-01-17
 
 ### Added
 - Type hints for all core library modules (utils_units, text_utils, config_loader, pk_indicator_rules)
 - mypy static type checking in CI pipeline
 - Comprehensive unit test suite with 70+ tests
 - pytest fixtures in conftest.py for shared test data
 - text_utils.py module with extracted pure functions for testability
 - GitHub Actions CI/CD pipeline with lint, type check, and test stages
 - Pre-commit hooks configuration (.pre-commit-config.yaml)
 - Coverage threshold (80%) with HTML report upload
 - CHANGELOG.md following Keep a Changelog format
 - Semantic versioning (0.2.0)
 - py.typed marker for PEP 561 compliance
 - Makefile and dev.ps1 for common development commands
 - GitHub Release workflow for automated releases
 
 ### Changed
 - Updated pyproject.toml with mypy configuration
 - Improved docstrings with Google-style format and examples
 - Enhanced flake8 configuration for better linting
 
 ## [0.1.0] - 2026-01-15
 
 ### Added
 - Initial release of EOM Template Tools pyRevit extension
 - Diagnostics panel for listing AR links
 - Light placement tools:
   - Place lights at room centers
   - Place lights in lift shafts
   - Place lights at entrance doors
 - Socket placement tools:
   - General sockets
   - Kitchen unit sockets
   - Kitchen general sockets
   - AC sockets
   - Wet room sockets
   - Low voltage sockets
 - Panel/switch placement:
   - Place panels above apartment doors
   - Place switches by doors
 - Configuration system with JSON rules
 - Link reader utilities for working with Revit links
 - Unit conversion helpers (mm/ft)
 - PK indicator rules for fire hydrant detection
 
 [Unreleased]: https://github.com/user/EOMTemplateTools/compare/v0.2.0...HEAD
 [0.2.0]: https://github.com/user/EOMTemplateTools/compare/v0.1.0...v0.2.0
 [0.1.0]: https://github.com/user/EOMTemplateTools/releases/tag/v0.1.0
