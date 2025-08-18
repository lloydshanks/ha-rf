# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Home Assistant custom integration that enables control of 433MHz/315MHz RF devices through GPIO pins on Raspberry Pi. It's a revival of the deprecated core Home Assistant `rpi_rf` integration.

## Architecture

- **Integration Type**: Home Assistant custom component (switch platform)
- **Core Module**: `custom_components/ha_rf/switch.py` - Contains the main `RPiRFSwitch` entity class
- **RF Module**: `custom_components/ha_rf/rf_device.py` - Embedded RF communication module (replaces external rpi-rf dependency)
- **Dependencies**: `rpi-lgpio>=0.6` (defined in `manifest.json`) - Modern GPIO library for Python 3.13 compatibility
- **Configuration**: YAML-based platform configuration in Home Assistant's `configuration.yaml`

### Key Components

- `RPiRFSwitch` class: Implements Home Assistant's `SwitchEntity` interface
- `RFDevice` class: Embedded RF communication with fallback GPIO library support (RPi.GPIO → rpi-lgpio)
- Thread-safe RF transmission using `RLock` for concurrent access
- Support for multiple RF protocols, pulse lengths, and signal repetitions
- Unique ID generation for Home Assistant entity management

## Development Commands

### Linting and Code Quality
```bash
# Install development dependencies with uv
uv sync

# Run all pre-commit hooks (recommended)
uv run pre-commit run

# Individual tools (all replaced by Ruff except mypy)
uv run ruff check .        # Linting, formatting, import sorting, and more
uv run ruff format .       # Code formatting
uv run mypy custom_components/  # Type checking (may have import errors for HA libs)
```

### Testing
- Tests run via GitHub Actions on Python 3.12 and 3.13
- Home Assistant validation via `hassfest` action
- HACS validation for custom component standards

## Configuration Schema

The integration uses Voluptuous schema validation with these key parameters:
- `gpio`: Required GPIO pin number
- `switches`: Dictionary of switch configurations
- Per-switch: `code_on`, `code_off`, `protocol`, `pulselength`, `length`, `signal_repetitions`, `unique_id`

## Code Style Guidelines

- Follow Home Assistant coding standards
- Use type hints (enforced by mypy --strict)
- Modern Ruff formatting and linting (replaces black, flake8, isort, pydocstyle, pyupgrade)
- Python 3.13+ compatible syntax
- Comprehensive docstrings and error handling

## Home Assistant Integration Patterns

- Platform setup via `setup_platform()` function
- Entity cleanup on Home Assistant stop event
- State management through `_state` attribute
- Proper use of `schedule_update_ha_state()` for UI updates
- Thread-safe hardware access patterns