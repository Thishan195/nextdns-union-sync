# 07 · Files explained

[⬅️ Back to index](README.md)

---

## 📄 At a glance

| File | Location | Required | Purpose |
|---|---|---|---|
| `union.py` | root | ⭐ ✅ | the whole program |
| `sync-state.json` | root | ⭐ ✅ | state DB — prevents duplicates |
| `.github/workflows/union-sync.yml` | `.github/workflows/` | ⭐ ✅ | the GitHub Action |
| `union-summary.json` | root | — | per-run result (not committed) |
| `union-sync.yml` | root | — | convenience copy of the workflow |
| `README.md` | root | — | front page |
| `tests/test_union.py` | `tests/` | — | 25 offline tests |
| `Instructions/*.md` | `Instructions/` | — | documentation |
| `.gitignore` | root | — | ignore caches and run output |

---

## 1. `union.py` — the program

| Section | Responsibility |
|---|---|
| `CONFIG` | defaults, all overridable by environment variables |
| `load_profiles()` | reads `NEXTDNS_API_KEYn` / `NEXTDNS_PROFILE_IDn` / `NEXTDNS_LABELn` |
| `request()` | HTTP with retries and 429 handling |
| `get_list()` | reads a list, following pagination cursors |
| `normalise()` | lowercases ids, de-duplicates, resolves `active` |
| `notify()` / `build_report()` | Telegram |
| `load_state()` / `save_state()` | the state DB |
| `sync_kind()` | ⭐ union-syncs one list across all profiles |
| `main()` | argument parsing, summary, report |
| `run_guarded()` | reports crashes instead of dying silently |

### The only lines you might edit

```python
MAX_PROFILES = 20                     # raise if you need more than 20 profiles
LISTS = ("allowlist", "denylist")     # do not change: the two supported lists
```

Everything else is configuration through variables.

---

## 2. `sync-state.json` — the memory

```json
{
  "version": 1,
  "updated": "2026-10-29T14:20:31Z",
  "profiles": {
    "ab12cd": {
      "allowlist": ["a.com", "b.com"],
      "denylist": ["ads.com"],
      "seeded": ["allowlist", "denylist"]
    },
    "ef34gh": {
      "allowlist": ["a.com"],
      "denylist": ["ads.com", "tracker.io"],
      "seeded": ["allowlist", "denylist"]
    }
  }
}
```

| Field | Meaning |
|---|---|
| `version` | schema version (1) |
| `updated` | when the file was last written (UTC) |
| `profiles.<id>.allowlist` | allow-domains ever synced to that profile |
| `profiles.<id>.denylist` | deny-domains ever synced to that profile |
| `profiles.<id>.seeded` | which lists have been read at least once |

### Why `seeded` exists

Without it, an **empty** list looks like "never read", so that profile would be treated
as a first run on every run and would never be filled.

```
profile 3 allowlist = 0 entries
   ↓
"not seeded yet" → every run is a "first run" → nothing is ever written
```

With `"seeded": ["allowlist"]` the script knows "empty but already read".

### Rules

| ✅ Do | ❌ Don't |
|---|---|
| let the workflow commit it | edit it by hand |
| start from `{"version":1,"profiles":{}}` | add it to `.gitignore` |
| delete it if it is corrupt | copy it between repositories |

---

## 3. `.github/workflows/union-sync.yml`

| Step | Purpose |
|---|---|
| `actions/checkout@v4` | get the repo |
| `actions/setup-python@v5` | Python 3.12 |
| **Check variables** | `union.py --check` |
| **Union sync** | the actual run (`dry_run` / `full` inputs) |
| **Commit state DB** | commits `sync-state.json` (3 push attempts) |
| **Telegram — job failed** | notifies on failure/cancel |
| **Job summary** | puts the log in the run summary |
| **Upload state + summary** | artifacts, kept 7 days |

### Important settings

```yaml
on:
  schedule:
    - cron: "0 */12 * * *"        # every 12 hours (00:00 and 12:00 UTC)
  workflow_dispatch:               # manual runs

permissions:
  contents: write                  # needed to commit the state DB

concurrency:
  group: nextdns-profile-union     # never two runs at once

timeout-minutes: 90
```

### How variables reach the script

```yaml
env:
  ALL_VARS: ${{ toJson(vars) }}
```

`_vars()` parses that JSON and merges it into the environment, so `NEXTDNS_API_KEY1`
resolves both in Actions and locally.

---

## 4. `union-summary.json`

Machine-readable result of one run:

```json
{
  "results": [
    {
      "kind": "allowlist",
      "union": 22,
      "added": {"Home": 0, "Phone": 8},
      "skipped": 0,
      "seeded": false,
      "errors": [],
      "written": 8
    }
  ],
  "problems": []
}
```

Not committed — download it from the run artifacts.

---

## 5. `union-sync.yml` (root)

A byte-identical copy of the workflow, placed at the root on purpose:

- tools that hide dot-folders still give you the content
- you can copy it into `.github/workflows/` from a phone

⚠️ GitHub **ignores** this file. Only `.github/workflows/union-sync.yml` is executed.

---

## 6. `tests/test_union.py` — 25 tests

```bash
python3 tests/test_union.py
```

```
PASS test_allow_and_deny_never_mix
PASS test_twenty_slots_are_supported
PASS test_empty_profile_is_filled_on_the_very_first_run
...
ALL TESTS PASS
```

No network, no keys, no Telegram — a fake API is used.

| Group | What is verified |
|---|---|
| variables | numbering, gaps, half-configured slots, labels, 20 slots |
| first run | seed + fill in one run, empty profiles |
| propagation | new domain reaches everyone, no duplicates |
| `full` | restores, respects deletes |
| separation | allowlist ≠ denylist |
| bulk | `PUT` vs `POST` |
| errors | duplicate 400, 500 retry, read failure |
| safety | no `DELETE`, no settings endpoints, dry-run writes nothing |
| telegram | one message per run, can be disabled |

---

## 7. `Instructions/`

| File | Topic |
|---|---|
| `README.md` | index |
| `01-WHAT-IS-THIS.md` | overview |
| `02-QUICK-START.md` | setup in 10 minutes |
| `03-VARIABLES.md` | all variables |
| `04-INSTALL.md` | where files go |
| `05-FULL-SYNC.md` | the emergency switch |
| `06-TELEGRAM.md` | bot setup |
| `07-FILES.md` | this file |
| `08-HOW-IT-WORKS.md` | internals |
| `09-TROUBLESHOOTING.md` | errors |
| `10-COMMANDS.md` | commands and curl |
| `11-FAQ.md` | questions |
| `12-SECURITY.md` | security |
| `13-TEMPLATE-GUIDE.md` | template + fork workflow |
