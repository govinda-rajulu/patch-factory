# Mechanic checklist (test gaps and one-line fixes, solo shift)

Trusted text, read into the Mechanic's shift prompt (src/council/seats.json `shift.checklist`).
Ideas adapted from affaan-m/ECC verification-loop and code-reviewer and cursor/plugins
Team Kit (both MIT), reviewed 22 Oct 2026; our own words, fitted to this repository.

1. Read the function and every caller and test that touches it before judging it.
2. A test gap counts only when you can name the input, the wrong result it lets through and
   the test file that should hold the check (tests/*_contracts.py).
3. A fix is the smallest change that makes that test pass; never weaken a check, a filter
   (src/patches/BANNED is substrings on purpose) or an error path to make something green.
4. Prefer an existing helper or the standard library over a new dependency.
5. Zero findings is a good answer. Say in the summary what you did not read.
