# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- CLI check PyPI at most once per day for a newer release and print one stderr line (`uv tool upgrade …`). Disabled with `AGENTS_NO_UPDATE_CHECK=1` or when `CI` is set; offline/timeout stays silent.

## [0.44.0] - 2026-09-04

See GitHub release notes. Note: GitHub tag `v0.44.0` exists; PyPI still lists `0.43.0` until republished.
