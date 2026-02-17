# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CleanTelegram is a Python CLI tool for managing and cleaning Telegram accounts using Telethon. It automates destructive actions (deleting conversations, leaving groups) while providing backup capabilities and reporting features.

## Development Commands

### Installation
```bash
# With uv (recommended)
uv sync
uv pip install -e .

# Or with pip
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Testing
```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_backup_cloud.py

# Run with coverage
uv run pytest --cov=clean_telegram
```

### Running the Application
```bash
# Interactive mode (recommended for testing)
cleantelegram --interactive

# Direct module execution
python -m clean_telegram

# Development runner
python run_clean_telegram.py
```

## Architecture

### Module Structure
- `cli.py` - Main entry point, argument parsing, command routing, auth configuration, Telegram client creation
- `backup.py` - Backup and export functionality (messages, participants, media, cloud upload)
- `cleaner.py` - Conversation and group cleaning logic
- `interactive.py` - Interactive menu system using Rich/Questionary
- `reports.py` - Report generation (groups, contacts) in CSV/JSON/TXT formats
- `ui.py` - Shared UI components and helpers

### Authentication Modes
The application supports two operation modes, automatically detected via `.env`:
1. **User Mode** (default): Requires `API_ID` and `API_HASH`, interactive login with phone + code
2. **Bot Mode**: Additionally requires `BOT_TOKEN`, actions limited to bot permissions

### Async Pattern
The entire application is built on asyncio. All Telegram API calls are async:
- Entry point: `main()` async function in `cli.py`
- Console scripts call `main_sync()` which wraps `asyncio.run(main())`

### Test Setup
- Tests use `pytest` with `pytest-asyncio` for async test support
- `tests/conftest.py` modifies `sys.path` to ensure `src/` is imported correctly
- When adding new tests, ensure the test file respects the path configuration

### Configuration
- Environment variables loaded via `python-dotenv` from `.env` file
- Required: `API_ID`, `API_HASH`
- Optional: `BOT_TOKEN`, `SESSION_NAME`, `BOT_SESSION_NAME`

### Optional Dependencies
- `orjson`: Faster JSON processing (2-3x faster than stdlib), installed via `pip install -e ".[optional]"`

### Safety Features
- `--dry-run` flag for safe testing without making changes
- Confirmation prompts for destructive actions
- Bot permission warnings when operations require elevated permissions

## Key Entry Points

1. **Console scripts**: `cleantelegram` or `clean-telegram` → `clean_telegram.cli:main_sync`
2. **Module**: `python -m clean_telegram` → `clean_telegram.__main__`
3. **Interactive**: `cleantelegram --interactive` → `clean_telegram.interactive:interactive_main`
