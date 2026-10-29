# NextDNS Profile Union

**Keep the allowlist and denylist of up to 20 NextDNS profiles in sync — automatically.**

Add a domain to any one profile and it is added to every other profile on the next run.
Allowlist + denylist only · add-only (nothing is ever deleted) · no duplicates · **no credentials in this repo**, so it can stay public.

> [!WARNING]
> ### 🍴 Forking? Make your fork **private**.
> This template contains **no keys** — they live in your GitHub *Variables*.
> Your fork **will** contain `sync-state.json`, which lists the exact domains you
> allow and block. Fork into a **private** repository so only you can see them.
> `sync-state.json` also changes on every run (the bot commits it), so a private fork
> saves you from a noisy public commit history.
>
> ![Fork → private](https://img.shields.io/badge/fork%20%E2%86%92-private%20repo-critical)
> **How:** `Fork` → in the *Create a new fork* screen choose **Owner: yourself**,
> then after creation go to **Settings → General → Danger Zone → Change repository visibility → Private**.

---

## ⚡ Quick start (3 minutes)

```
1. Fork / create a repo (private, see the warning above)
2. Add the files: union.py · sync-state.json · .github/workflows/union-sync.yml
3. Settings → Secrets and variables → Actions → Variables:
       NEXTDNS_API_KEY1     = <your api key>
       NEXTDNS_PROFILE_ID1  = <your profile id>
4. Settings → Actions → General → Workflow permissions → Read and write
5. Actions → Run workflow → dry_run = true (look) → then dry_run = false (apply)
```

That's it. It now runs every 12 hours on its own.

📖 **Full documentation → [`Instructions/`](Instructions/README.md)**

---

## What gets synced

| ✅ Synced | ❌ Never touched |
|---|---|
| **allowlist** | settings / security / privacy |
| **denylist** | blocklists / parental control |

> Settings are deliberately excluded: syncing them between profiles usually causes
> surprises (one profile wants logging, another does not). The two domain lists are safe.

---

## Features

- 🔗 **Union** — add a domain to one profile and every profile gets it
- ➕ **Add-only** — never deletes an entry, never flips a toggle off
- 🗄️ **No duplicates** — `sync-state.json` in the repo remembers every domain
- 🖐️ **Respects your deletes** — a domain you removed by hand is never re-added
- 📦 **Bulk PUT** — 20+ items go in a single request (125 domains = ~2 s instead of 21 min)
- 🔁 **Error-safe** — duplicates and 5xx responses are skipped, one bad profile never stops the run
- 📩 **Telegram reports** — an optional message after every run (success **and** failure)
- 🔑 **Variables-only** — no secrets in the code, so the repo can be public
- ⏰ **Every 12 hours** (cron) plus manual runs

---

## Variables

Everything is configured with GitHub **Variables** — never in the code.
See [`Instructions/03-VARIABLES.md`](Instructions/03-VARIABLES.md) for the full reference.

| Variable | Required | Example | Meaning |
|---|---|---|---|
| `NEXTDNS_API_KEY1` … `NEXTDNS_API_KEY20` | ✅ | `0123456789abcdef…` | API key that can read profile N |
| `NEXTDNS_PROFILE_ID1` … `NEXTDNS_PROFILE_ID20` | ✅ | `ab12cd` | the profile id (from `my.nextdns.io/ab12cd/settings`) |
| `NEXTDNS_LABEL1` … `NEXTDNS_LABEL20` | — | `Phone` | friendly name used in reports |
| `TG_TOKEN` | — | `1234567890:AAHxxxx…` | Telegram bot token |
| `TG_CHAT` | — | `123456789` | your Telegram user id |
| `TG_ON` | — | `true` | `false` disables Telegram reports |

Tuning (all optional, good defaults):
`SYNC_DELAY` (10) · `SYNC_READ_DELAY` (0.5) · `SYNC_BACKFILL` (true) ·
`SYNC_BULK_THRESHOLD` (20) · `SYNC_RETRIES` (4) · `SYNC_TIMEOUT` (30) ·
`SYNC_APPLY` (true) · `SYNC_STATE_PATH` · `SYNC_SUMMARY_PATH`

> ⚠️ **Secrets vs Variables** — this project reads **Variables**
> (`Settings → Secrets and variables → Actions → *Variables* tab`).
> Adding them under *Secrets* will not work.

---

## Files

```
union.py                            main script (no credentials inside)
sync-state.json                     the state DB — {"version":1,"profiles":{}}
.github/workflows/union-sync.yml    the GitHub Action   ⚠️ hidden folder
tests/test_union.py                 offline tests (25, no network needed)
Instructions/                       full documentation (13 files)
union-sync.yml                      convenience copy of the workflow (plain root file)
```

⚠️ GitHub only reads workflows from **`.github/workflows/`**. The root `union-sync.yml`
is there so tools that hide dot-folders (Windows Explorer, some ZIP managers) still
give you the content to copy. See [`Instructions/04-INSTALL.md`](Instructions/04-INSTALL.md).

---

## Commands (local)

```bash
python3 union.py --check      # verify variables
python3 union.py --list       # verify keys + show profile names
python3 union.py --dry-run    # show what would be added (writes nothing)
python3 union.py              # apply
python3 union.py --full       # ignore the state DB (emergency, see 05-FULL-SYNC)
python3 union.py --no-notify  # skip the Telegram message
python3 tests/test_union.py   # 25 offline tests
```

---

## Quick fixes

| Symptom | Fix |
|---|---|
| The workflow does not appear in *Actions* | Check `.github/workflows/` — the folder name starts with a **dot** |
| `Commit state DB` fails with **403** | Settings → Actions → General → Workflow permissions → **Read and write** |
| Domains are re-added on every run | Same as above — the state DB is not being committed |
| `No profile was found` | Add the variables to the **Variables** tab (not *Secrets*) |
| A new domain was not synced | The run happened before you added it — wait or run manually |
| When should I use `full`? | [`Instructions/05-FULL-SYNC.md`](Instructions/05-FULL-SYNC.md) |

📖 40+ errors explained → [`Instructions/09-TROUBLESHOOTING.md`](Instructions/09-TROUBLESHOOTING.md)

---

## Security

- ❌ No API keys or bot tokens in the repository — they live in GitHub **Variables**
- ✅ `permissions: contents: write` only (just enough to commit the state DB)
- ✅ GitHub-official actions only (no third-party supply chain)
- ⚠️ `sync-state.json` contains your domains (not your keys) — keep the repo private if that matters

📖 [`Instructions/12-SECURITY.md`](Instructions/12-SECURITY.md)

---

## How it works (one line)

Every 12 hours: read both lists from every profile → build the union → add whatever each
profile is missing (bulk `PUT` for large batches, `POST` + 10 s cooldown for small ones) →
save the state DB → send a report.

📖 [`Instructions/08-HOW-IT-WORKS.md`](Instructions/08-HOW-IT-WORKS.md)

---

## License

GPL-3.0
