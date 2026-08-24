# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4-alpha] - 2026-08-24
### Fixed
- Fixed a bug in `scheduler.py` where a `sqlite3.Row` key check failed, causing the `fokiz-monitor` service to crash silently.
- Fixed a bug in `notifier.py` where the notification urgency parameter was ignored and hardcoded to "critical".

## [0.9.0] - 2026-08-22
### Fixed
- Fixed critical i18n regression where internal string keys were exposed in CLI output instead of localized strings.
- Refactored `messages.py` to route all status messages through the centralized i18n registry.
- Updated `ui.py` to correctly utilize `board.*` namespaces for i18n keys.
- Added comprehensive unit tests for the internationalization system (`tests/test_i18n.py`).
- Completely removed residual Spanish strings from code logic, enforcing translation exclusively via `i18n.py`.
## [0.4.0] - 2026-08-21
### Changed
- Updated Fokiz ASCII art to a new, compact design.
- Fixed UI rendering for missing escape sequences.

## [0.3.0] - 2026-08-21
### Added
- Multi-language support (English and Spanish) via `i18n.py`.

### Changed
- Translated all residual Spanish code comments to English.
- Re-architected `install.sh` and `install.py` to fix installation bugs (`git fetch` logic and Python imports).
## [0.2.0] - 2026-08-21
### Added
- GitHub update checker in `updater.py` that alerts on `fokiz status` if a new version is available.
- Full `install.sh` standard curl-to-bash script.
- GitHub Actions for testing and releases.
- Open Source standard docs (`docs/`): Contributing, Security, and Code of Conduct.

### Changed
- Improved `fokiz status` UI to handle dynamic messaging.
- Migrated code out of early prototype into modular structure (commands, daemon, constants, config, messages).
- Upgraded license to GNU GPL v3 for Alenia Studios.

## [0.1.0] - 2026-08-01
### Added
- Initial proof of concept.
- Ulysses contract mechanics via `systemd` daemon.
- Hard penalties executing arbitrary scripts on breach.
- SQLite database for contract status tracking.
