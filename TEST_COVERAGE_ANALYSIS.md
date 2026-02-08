# Test Coverage Analysis

This analysis covers both the current `main` branch and the incoming PR #3 (`feat/qr-login`), which significantly restructures the codebase.

---

## Part 1: Current `main` Branch

### Before improvements

**Overall coverage: 59%** (478 of 1,160 statements missed) | 66 tests (65 passing, 1 failing)

### After improvements

**Overall coverage: 80%** (231 of 1,160 statements missed) | 147 tests (all passing)

| Module | Stmts | Before | After | Change |
|--------|-------|--------|-------|--------|
| `__init__.py` | 1 | 100% | 100% | -- |
| `__main__.py` | 6 | 0% | 0% | (thin wrapper) |
| `backup.py` | 477 | 64% | 64% | -- |
| `cleaner.py` | 74 | 85% | **97%** | +12pp |
| `cli.py` | 204 | 45% | **99%** | +54pp |
| `interactive.py` | 182 | 24% | **77%** | +53pp |
| `reports.py` | 170 | 91% | **97%** | +6pp |
| `ui.py` | 46 | 52% | **100%** | +48pp |

### What was fixed and added

**Fixed:** `test_should_include_media_count_in_summary` -- was patching `download_media_from_chat` instead of `download_media_parallel`.

**New test files:**
- `test_cli_extended.py` -- env_int, parse_args, confirm_action, run_report, run_clean, run_backup, main() integration
- `test_cleaner_extended.py` -- unknown entity type, RPCError/Exception handlers
- `test_reports_extended.py` -- generate_all_reports, contacts default path, _safe_getattr
- `test_interactive_extended.py` -- interactive_clean, interactive_reports, interactive_stats, menu dispatch, backup happy path
- `test_ui.py` -- suppress_telethon_logs, print_header, print_stats_table, all print_* functions

### Remaining gaps on `main`

1. **`backup.py` (64%)** -- The largest remaining gap. Untested: `export_messages_to_json()`, `export_messages_to_csv()`, `export_participants_to_json()`, `export_participants_to_csv()`, `download_media_from_chat()`, `backup_group_full()`, and the `ChatAdminRequiredError` path.
2. **`interactive.py` (77%)** -- Some deeper flows remain: custom path input for reports, media type "custom" selection in backup, the backup result display with media counts.
3. **`cleaner.py` (97%)** -- Only 2 lines uncovered (FloodWait sleep path in retry loop).

---

## Part 2: PR #3 (`feat/qr-login` branch)

PR #3 replaces the entire module structure. The backup, cleaner, cli, interactive, reports, and ui modules are all removed and replaced with a focused architecture:

| Module | Stmts | Miss | Branch Miss | Coverage | Status |
|--------|-------|------|-------------|----------|--------|
| `__init__.py` | 4 | 0 | 0 | 100% | Fully covered |
| `__main__.py` | 105 | 36 | 2 | 66% | Partial |
| `client.py` | 52 | 0 | 2 | 97% | Excellent |
| `utils.py` | 48 | 0 | 0 | 100% | Fully covered |

**Overall coverage: 83%** (36 of 209 statements missed)
**Existing tests:** 51 total (all passing)

This is a much smaller, more focused codebase -- but the 36 uncovered lines are concentrated in the most critical new feature.

### Gap Analysis

#### 1. `__main__.py`: `display_qr_code()` -- 0% coverage (lines 26-34)

The QR code display function is the core of the new feature and has **zero tests**.

```python
def display_qr_code(url: str) -> None:
    qr = qrcode.QRCode(...)
    qr.add_data(url)
    qr.print_ascii(invert=True)
    print(f"\nURL: {url}\n")
```

**Recommended tests:**
- `test_display_qr_code_prints_url` -- Capture stdout and verify the URL appears in output
- `test_display_qr_code_calls_qrcode_library` -- Mock `qrcode.QRCode` and verify `add_data()` and `print_ascii()` are called

#### 2. `__main__.py`: `login_with_qr()` -- 0% coverage (lines 46-75)

The entire QR login flow is untested. This is the primary feature of PR #3.

```python
async def login_with_qr(client: TelegramClient) -> bool:
    qr_login = await client.qr_login()
    while not qr_login.is_logged:
        display_qr_code(qr_login.url)
        try:
            await asyncio.wait_for(qr_login.wait(), timeout=10)
        except asyncio.TimeoutError:
            continue  # BUG: redisplays same expired QR without recreating
        except SessionPasswordNeededError:
            return False
        except Exception as e:
            return False
    return True
```

**Issues identified by CodeRabbit review (confirmed):**
- **No max-attempts guard**: The `while` loop can run indefinitely if QR is never scanned
- **QR refresh bug**: On `TimeoutError`, the code re-displays the same expired QR URL instead of calling `qr_login.recreate()`
- **Session name bug**: `session_name.replace(".session", "")` at line 127 removes intermediate occurrences; should use `removesuffix(".session")`

**Recommended tests:**
- `test_login_with_qr_success` -- Mock `client.qr_login()` returning object where `wait()` completes, verify returns `True`
- `test_login_with_qr_timeout_regenerates` -- Mock timeout on first attempt, success on second; verify `display_qr_code` called twice
- `test_login_with_qr_2fa_returns_false` -- Mock `SessionPasswordNeededError`, verify returns `False`
- `test_login_with_qr_generic_error_returns_false` -- Mock generic `Exception`, verify returns `False`
- `test_login_with_qr_max_attempts` -- Once the max-attempts guard is added, test that the loop exits after N failures

#### 3. `__main__.py`: QR session name handling (lines 127-128)

```python
base_name = session_name.replace(".session", "")
session_name = f"{base_name}_qr.session"
```

**Recommended tests:**
- `test_qr_login_session_name_simple` -- Input `"session"` -> `"session_qr.session"`
- `test_qr_login_session_name_with_suffix` -- Input `"my.session"` -> should produce `"my_qr.session"`, not `"my_qr.session"` from removing inner `.session`
- `test_qr_login_session_name_with_path` -- Input `"/home/user/.clean_telegram/session"` -> correct QR variant

#### 4. `__main__.py`: Error handling in main loop (lines 198-204)

The `RPCError` and generic `Exception` handlers in the dialog iteration loop are not covered:

```python
except RPCError:
    logger.exception("RPCError em '%s'", title)
    break
except Exception:
    logger.exception("Erro inesperado em '%s'", title)
    break
```

While `test_main_rpc_error_handling` exists, it patches `process_dialog` at the module level, meaning the `except RPCError` at line 198 catches the error raised by the mock -- but the `except Exception` at line 202 is never triggered because the RPCError catch comes first. A test that raises a non-RPC exception (e.g., `ConnectionError`) would cover line 202-204.

**Recommended tests:**
- `test_main_generic_exception_in_dialog_loop` -- Mock `process_dialog` to raise `RuntimeError`, verify it's caught and loop continues

#### 5. `client.py`: Branch coverage gaps (97% line coverage, 2 branch misses)

Two branch partial misses at lines 95->97 and 105->107. These are the `if not dry_run:` branches in the unknown-entity-type handler. The current tests pass `dry_run=False` for `test_process_unknown_type`, so the `dry_run=True` path for unknown entities is untested.

**Recommended test:**
- `test_process_unknown_type_dry_run` -- Verify that unknown entity types in dry-run mode still return `True` without calling `client.delete_dialog`

---

## Prioritized Recommendations for PR #3

### Priority 1 -- Critical (blocks merge)

1. **Add tests for `login_with_qr()`** -- This is the feature being added and has 0% coverage. At minimum, test the success path, 2FA rejection, and generic error path.

2. **Add tests for `display_qr_code()`** -- Simple function, easy to test by mocking `qrcode.QRCode` or capturing stdout.

3. **Fix the QR refresh bug** -- On `TimeoutError`, the code should call `qr_login.recreate()` before looping. Add a test that verifies this.

4. **Fix `session_name.replace(".session", "")`** -- Replace with `removesuffix(".session")` (Python 3.9+). Add a test with a session name containing `.session` in the middle.

5. **Add a max-attempts safeguard to `login_with_qr()`** -- The infinite loop is a risk. Add `max_attempts` parameter with default (e.g., 30 for ~5 minutes at 10s intervals), and test that it exits.

### Priority 2 -- Important

6. **Test the generic exception handler in the main loop** -- Cover lines 202-204 with a `RuntimeError` or `ConnectionError` mock.

7. **Test unknown entity dry-run branch** -- Cover the 2 branch misses in `client.py` for full branch coverage.

8. **Test `--qr-login` flag integration** -- Verify that `main()` correctly enters the QR login flow when `--qr-login` is passed.

### Priority 3 -- Nice to have

9. **Integration test for full QR login flow** -- Mock `TelegramClient.qr_login()` end-to-end through `main()`.

10. **Edge case: QR login when already authenticated** -- What happens if the user is already logged in but passes `--qr-login`?

---

## Infrastructure Recommendations

### For both branches

- **Add `[tool.coverage]` config to `pyproject.toml`** -- Define `fail_under` threshold to prevent regressions.
- **Add CI coverage gate** -- Run `pytest --cov=clean_telegram --cov-fail-under=80` in CI.

### Specific to PR #3

- The PR already has good fixture organization in `conftest.py` (shared `mock_telegram_client`, `mock_channel`, `mock_chat`, `mock_user`, `mock_bot`, `mock_dialog_factory`).
- The `monkeypatch_env` fixture is well-designed for environment variable testing.
- Consider adding a `mock_qr_login` fixture to `conftest.py` for the new QR tests.

### Specific to `main` branch (if PR #3 doesn't merge)

- Consolidate `AsyncIteratorMock` -- duplicated in 3 test files; move to `conftest.py`.
- Centralize mock client/entity factories in `conftest.py`.
- Fix the failing `test_should_include_media_count_in_summary` test.
