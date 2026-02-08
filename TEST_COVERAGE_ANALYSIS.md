# Test Coverage Analysis

## Current State

**Overall coverage: 59%** (478 of 1,160 statements missed)

| Module | Stmts | Miss | Coverage | Status |
|--------|-------|------|----------|--------|
| `__init__.py` | 1 | 0 | 100% | Fully covered |
| `__main__.py` | 6 | 6 | 0% | No tests |
| `backup.py` | 477 | 173 | 64% | Partial |
| `cleaner.py` | 74 | 11 | 85% | Good |
| `cli.py` | 204 | 112 | 45% | Low |
| `interactive.py` | 182 | 139 | 24% | Very low |
| `reports.py` | 170 | 15 | 91% | Good |
| `ui.py` | 46 | 22 | 52% | Low |

**Existing tests:** 66 total (65 passing, 1 failing)

The failing test (`test_should_include_media_count_in_summary`) patches `download_media_from_chat` but the production code calls `download_media_parallel` instead, so the mock never takes effect and `results["media"]` is never populated.

---

## Gap Analysis by Module

### 1. `cli.py` (45% coverage -- high priority)

The CLI module is the main entry point and nearly half of it is untested.

**Untested code:**

- **`parse_args()`** (lines 50-149) -- The entire argument parser is never exercised. While argument parsing is often boilerplate, testing it catches issues with conflicting flags, missing defaults, and wrong types.

- **`env_int()`** (lines 37-45) -- The helper that reads required integer environment variables has no tests. Edge cases to cover: missing variable (should `SystemExit`), non-integer value (should `SystemExit`), valid integer.

- **`confirm_action()`** (lines 188-197) -- The stdin-based confirmation prompt is untested.

- **`run_report()`** (lines 236-274) -- The orchestrator that calls report generation based on CLI args. Tests should verify correct dispatch for `--report groups`, `--report contacts`, and `--report all`.

- **`run_clean()`** (lines 277-292) -- The orchestrator that calls `clean_all_dialogs`. Simple to test with mocks.

- **`run_backup()`** (lines 295-414) -- The largest untested function. It handles:
  - Resolving chat entity from `--backup-group`, `--export-members`, `--export-messages`
  - Error handling when the entity can't be resolved
  - Media type parsing from `--media-types`
  - Dispatching to the correct export functions
  - Logging output formatting

- **`main()`** (lines 417-478) -- The top-level async entry point that wires everything together. Integration-level tests covering the main flow (interactive mode, backup mode, report mode, clean mode with confirmation) would be valuable.

**Recommended tests:**
- `test_env_int_missing_var` / `test_env_int_invalid_value` / `test_env_int_valid`
- `test_parse_args_defaults` / `test_parse_args_all_options`
- `test_confirm_action_accepts` / `test_confirm_action_rejects`
- `test_run_report_groups` / `test_run_report_contacts` / `test_run_report_all`
- `test_run_clean_calls_clean_all_dialogs`
- `test_run_backup_group` / `test_run_backup_export_members` / `test_run_backup_export_messages`
- `test_run_backup_entity_not_found`
- `test_run_backup_media_types_parsing`
- `test_main_interactive_mode` / `test_main_clean_mode_with_confirmation`

### 2. `interactive.py` (24% coverage -- high priority)

This is the least-covered module. Only the `interactive_backup` function has basic tests (cancel scenarios), and the main menu has two shallow tests.

**Untested functions:**

- **`interactive_clean()`** (lines 100-167) -- The entire clean flow: confirmation prompts, dry-run selection, limit selection, execution, error handling. No tests at all.

- **`interactive_reports()`** (lines 170-243) -- The report generation flow: type selection, format selection, custom path, execution, error handling. No tests.

- **`interactive_stats()`** (lines 246-299) -- Account statistics display: user info, dialog counting by type. No tests.

- **`interactive_main()`** -- Only tested for the "backup" and "exit" actions. The "clean", "reports", and "stats" menu branches are untested.

- **`interactive_backup()` deeper flows** -- The existing tests only cover cancellation. The happy path (selecting format, choosing media types including "custom" selection, enabling cloud backup, confirming, and executing) is completely untested.

**Recommended tests:**
- `test_interactive_clean_dry_run` / `test_interactive_clean_cancel_at_confirmation` / `test_interactive_clean_cancel_at_limit`
- `test_interactive_reports_groups_csv` / `test_interactive_reports_cancel`
- `test_interactive_stats_displays_counts`
- `test_interactive_main_clean_dispatch` / `test_interactive_main_reports_dispatch` / `test_interactive_main_stats_dispatch` / `test_interactive_main_exit`
- `test_interactive_backup_happy_path_json` / `test_interactive_backup_with_media_custom_types` / `test_interactive_backup_with_cloud`

### 3. `backup.py` (64% coverage -- medium priority)

The backup module is large (477 statements) and has partial coverage. The streaming and parallel-download paths are tested, but several core functions are not.

**Untested functions/paths:**

- **`export_messages_to_json()`** (lines 129-164) -- The non-streaming JSON export. No direct tests (the streaming variant is tested instead).

- **`export_messages_to_csv()`** (lines 207-269) -- The CSV message export. Only tested indirectly through `backup_group_with_media` in the cloud tests, but no dedicated tests verifying CSV content correctness.

- **`export_participants_to_json()`** (lines 272-307) -- The non-streaming participant JSON export. Not tested directly.

- **`export_participants_to_csv()`** (lines 350-417) -- Participant CSV export. No direct tests for content correctness.

- **`backup_group_full()`** (lines 420-482) -- The original backup function (without media support). Appears to be a dead code path since `backup_group_with_media` replaced it, but if it's still part of the public API it should be tested.

- **`download_media_from_chat()`** (lines 485-613) -- The sequential media download function. Not tested directly (only the parallel variant has tests).

- **`_serialize_message()`** edge cases -- Media type detection, sender info, reply_to handling.

- **`_serialize_participant()`** edge cases -- User with `participant` metadata (joined_date, inviter_id, admin_rank), User with online status (`expires`).

- **Error path in `backup_group_with_media()`** (lines 1132-1143) -- The `ChatAdminRequiredError` handling for participant export. Not covered.

- **`_json_dumps()`** fallback path (line 41) -- The stdlib json fallback when orjson is unavailable.

**Recommended tests:**
- `test_export_messages_to_json_content` / `test_export_messages_to_json_empty`
- `test_export_messages_to_csv_content` / `test_export_messages_to_csv_with_media`
- `test_export_participants_to_json_content`
- `test_export_participants_to_csv_content` / `test_export_participants_to_csv_with_metadata`
- `test_serialize_message_with_media` / `test_serialize_message_with_reply`
- `test_serialize_participant_with_online_status` / `test_serialize_participant_with_join_date`
- `test_backup_group_with_media_admin_required_error`
- `test_download_media_from_chat_sequential`
- `test_download_media_type_filtering`

### 4. `ui.py` (52% coverage -- low priority)

The UI module is mostly thin wrappers around Rich. The untested functions are:

- **`print_header()`** (lines 47-57) -- Panel display with optional subtitle
- **`print_stats_table()`** (lines 60-85) -- Table display with number formatting (including the `ValueError` fallback at line 80)
- **`print_success/error/warning/info/tip()`** (lines 88-110) -- One-line formatting functions

These are presentation-only functions. Testing them provides limited value since they just call `console.print()`. If coverage numbers matter, they can be tested by capturing Rich console output, but functionally they are low risk.

**Recommended tests (if desired):**
- `test_print_stats_table_formats_integers`
- `test_print_header_with_subtitle` / `test_print_header_without_subtitle`
- `test_suppress_telethon_logs_restores_level`

### 5. `cleaner.py` (85% coverage -- low priority)

Good coverage overall. The uncovered lines are:

- **Lines 87-89** -- The "unknown entity type" fallback in `_process_dialog()` where the entity is not a Channel, Chat, or User. This path calls `client.delete_dialog(entity)` for any unrecognized type.
- **Lines 145-154** -- The `RPCError` and generic `Exception` handlers inside the retry loop in `clean_all_dialogs()`. Only the `FloodWaitError` retry path is tested; the error-logging-and-break paths for `RPCError` and unexpected `Exception` are not.

**Recommended tests:**
- `test_process_dialog_unknown_entity_type`
- `test_clean_all_dialogs_rpc_error_breaks_loop`
- `test_clean_all_dialogs_unexpected_exception_breaks_loop`

### 6. `reports.py` (91% coverage -- low priority)

Well covered. The only uncovered lines are:

- **Lines 25-26** -- The `_safe_getattr` fallback (same function exists in backup.py too)
- **Line 169** -- A fallback branch in `_format_status`
- **Lines 191-193, 207** -- Default path generation in `generate_contacts_report` and the unreachable `else` branch
- **Lines 394-404** -- `generate_all_reports()` function

**Recommended tests:**
- `test_generate_all_reports` -- Verify it generates both reports
- `test_generate_contacts_report_default_path` -- Like the groups test but for contacts

---

## Prioritized Recommendations

### Priority 1 -- High impact, low effort

1. **`cli.py`: `env_int()`, `run_report()`, `run_clean()`** -- Small functions, easy to mock, currently at 0% coverage for core dispatch logic.

2. **`cli.py`: `run_backup()` happy path** -- The most complex untested function. A single integration-style test covering `--backup-group` with media would cover ~50 lines.

3. **`cleaner.py`: error handling paths** -- Three small tests to cover RPCError and Exception handlers in the retry loop.

4. **Fix the failing test** -- `test_should_include_media_count_in_summary` patches the wrong function (`download_media_from_chat` instead of `download_media_parallel`).

### Priority 2 -- Medium impact

5. **`interactive.py`: `interactive_clean()` and `interactive_reports()`** -- These are user-facing flows with error handling that should be verified.

6. **`backup.py`: direct export function tests** -- `export_messages_to_csv`, `export_participants_to_csv`, and their JSON counterparts should have content-verification tests.

7. **`backup.py`: ChatAdminRequired error path** -- Verify graceful degradation when participant listing requires admin.

### Priority 3 -- Coverage completeness

8. **`interactive.py`: happy paths for all menu options** -- These require significant mock setup for questionary but ensure the interactive flows work end-to-end.

9. **`backup.py`: `_serialize_message()` and `_serialize_participant()` edge cases** -- Media types, reply chains, participant metadata.

10. **`ui.py`: presentation functions** -- Low risk, but easy to test if coverage targets require it.

---

## Infrastructure Recommendations

- **Add `[tool.coverage]` config to `pyproject.toml`** -- Define source paths, omit patterns, and fail-under thresholds.
- **Add a CI step for coverage** -- Run `pytest --cov=clean_telegram --cov-fail-under=70` to prevent regressions.
- **Consolidate `AsyncIteratorMock`** -- This helper is duplicated across `test_cleaner.py`, `test_backup_cloud.py`, and `test_performance.py`. Move it to `conftest.py`.
- **Create a shared fixtures module** -- Mock client factories and mock entity factories are duplicated. Centralize them in `conftest.py`.
