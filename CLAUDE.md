# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

Interactive CLI utility for normalizing and splitting HR export CSV files (Users and Job Assignments) before they are imported into downstream systems. Tenant-specific records are extracted into separate output files with an auto-enrollment column added.

## Commands

```powershell
# Run the main interactive CLI (no tenant splitting)
python Main.py

# Run with one or more tenant IDs (case-insensitive, must exist in tenants.json)
python Main.py jbg
python Main.py jbg jaa
```

After launch, paste a CSV path at the prompt (surrounding quotes are stripped automatically). Enter `q` to quit. The filename **must** contain either `Users` or `Job Assignments` (case-insensitive) — that substring is what routes processing, not the file contents.

There is no test suite, linter config, or build step. Type checking uses [pyrightconfig.json](pyrightconfig.json) (relaxed: unknown member/variable/argument types are silenced). Only runtime dependency is `pandas`.

## Architecture

Three modules form the pipeline; [Main.py](Main.py) is the entry point.

1. **[Tenants.py](Tenants.py) — `load_tenants()`** reads [tenants.json](tenants.json) using a path resolved relative to the script file (not CWD), so the CLI works from any working directory. `tenant_id` is lowercased on load; tenants without an ID are filtered out.

2. **[Main.py](Main.py)** validates CLI tenant arguments against the loaded tenant list (raises `ValueError` on unknown ID), then enters a `read filename → HRImport(filename).run(tenants) → repeat` loop.

3. **[HrImport.py](HrImport.py) — `HRImport.run()`** dispatches on the filename substring:
   - `Job Assignments` → `_job_assignments()`: drops rows with missing `useridnumber`, fills `Manager email` NaN with `"#N/A"`, lowercases `Manager email` and `useridnumber`.
   - `Users` → `_users(tenants)`: drops rows with missing `idnumber`, then calls `_split_tenant()` for each tenant (which mutates `self.data` by removing matched rows), then lowercases `idnumber` and `email`.
   - Both paths drop rows where `idnumber` equals the hardcoded test accounts `joeben@joby.aero` or `patryck.chipman@joby.aero`.

   **The original CSV is overwritten in place** by `self.data.to_csv(self.filename)` at the end of `run()`. There is no backup.

### Tenant splitting (`_split_tenant`)

For each tenant, rows where `business unit description` (case-insensitive, trimmed) matches `tenant["business_unit_description"]` are written to a sibling file `<original>_<tenant_id>.csv` with an added `tenantmember` column set to the tenant ID. Those rows are removed from `self.data` so subsequent tenants and the final overwrite don't see them. The `tenantmember` column is the signal downstream systems use for auto-enrollment.

### Standalone scripts

- [not_in_both.py](not_in_both.py): unrelated one-off — prompts for two CSV paths (active, suspended) and prints rows of the first whose `idnumber` also appears in the second. Not wired into `Main.py`.

## Conventions worth preserving

- Filename-as-router: callers rely on the substring check in `run()`. Renaming an input file in a way that loses `Users` / `Job Assignments` will break processing with `ValueError`.
- Column names are hardcoded and case-sensitive: `useridnumber`, `idnumber`, `email`, `Manager email`, `business unit description`. Schema drift in the source export will surface as `KeyError`.
- Test-account filter list lives inline in both `_job_assignments` and `_users` — keep them in sync if extending.
