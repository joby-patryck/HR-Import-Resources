"""
LEGACY standalone diagnostic — NOT part of the main import pipeline.

This script is a one-off sanity check that finds accounts appearing in BOTH the
"active" and "suspended/terminated" exports — i.e. rows whose `idnumber` shows up
in both files. Such an account is contradictory (it cannot be active and
suspended at once), so a non-empty result flags data to investigate upstream
before importing.

It is intentionally simple and interactive: run it directly, paste the two file
paths at the prompts, and it prints the overlapping rows. It is not imported by
Main.py / App.py and shares no code with HRImport.py — kept only as a manual
debugging aid. New hires can safely ignore it for the normal workflow.

Usage:
    python not_in_both.py
    <paste path to the ACTIVE accounts CSV>
    <paste path to the SUSPENDED accounts CSV>
"""
import pandas

# Prompt 1: path to the ACTIVE accounts CSV (strip surrounding quotes file explorers add).
filenname_active = input().strip('"')
data_active = pandas.read_csv(filenname_active)
active_emails = data_active["idnumber"]

# Prompt 2: path to the SUSPENDED/terminated accounts CSV.
filenname_suspended = input().strip('"')
data_suspened = pandas.read_csv(filenname_suspended)
suspended_emails = data_suspened["idnumber"]

# Boolean mask: True for each active idnumber that ALSO appears in the suspended file.
# An account in both lists is contradictory ("quantum" — active and suspended at once).
in_both = data_active["idnumber"].isin(data_suspened["idnumber"])

# Keep only the contradictory rows and print them for manual review (empty == clean data).
result = data_active[in_both]

print(result)