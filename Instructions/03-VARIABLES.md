# 03 · Variables — the complete reference

[⬅️ Back to index](README.md)

---

## 📍 Where they live

```
Repo → Settings → Secrets and variables → Actions → "Variables" tab
                                                    ^^^^^^^^^^^^^^
                                                  not the Secrets tab
```

| | Variables | Secrets |
|---|---|---|
| Reference in workflow | `${{ vars.NAME }}` / `toJson(vars)` | `${{ secrets.NAME }}` |
| Visible in the UI | ✅ yes | ❌ hidden after saving |
| Visible in logs | ✅ yes (masked only if registered as a secret) | ❌ masked |
| Used by this project | ✅ **Variables** | ❌ not used |

> 🧠 **Why Variables?** The script reads configuration from the environment, and the
> workflow hands it every variable at once with `ALL_VARS: ${{ toJson(vars) }}`.
> Nothing sensitive is ever written into the repository. If you would rather use
> Secrets, change `toJson(vars)` to `toJson(secrets)` in the workflow — no code change needed.

---

## 🔑 Profiles (required)

Pattern: `NEXTDNS_<TYPE><N>` where **N = 1 … 20**

| # | Variable | Required | Example | Meaning |
|---|---|---|---|---|
| 1 | `NEXTDNS_API_KEYn` | ✅ | `0123456789abcdef…` | API key that can read profile N |
| 2 | `NEXTDNS_PROFILE_IDn` | ✅ | `ab12cd` | the profile id |
| 3 | `NEXTDNS_LABELn` | — | `Phone` | friendly name used in logs/reports |

### Example: four profiles

```
NEXTDNS_API_KEY1      = 0123456789abcdef0123456789abcdef01234567
NEXTDNS_PROFILE_ID1   = ab12cd
NEXTDNS_LABEL1        = Home

NEXTDNS_API_KEY2      = 89abcdef0123456789abcdef0123456789abcdef
NEXTDNS_PROFILE_ID2   = ef34gh
NEXTDNS_LABEL2        = Phone

NEXTDNS_API_KEY3      = fedcba9876543210fedcba9876543210fedcba98
NEXTDNS_PROFILE_ID3   = ij56kl
NEXTDNS_LABEL3        = Laptop

NEXTDNS_API_KEY4      = 00112233445566778899aabbccddeeff00112233
NEXTDNS_PROFILE_ID4   = mn78op
NEXTDNS_LABEL4        = TV
```

### Rules

| Rule | Detail |
|---|---|
| **Numbers do not have to be consecutive** | `1, 2, 7` is fine — the script checks 1–20 and uses whichever are complete |
| **Both key and id are required** | A slot with only one of the two is reported and skipped (the rest still run) |
| **One key, several profiles** | Profiles in the same NextDNS account share one key — reuse it for several slots |
| **More than 20** | Raise `MAX_PROFILES = 20` in `union.py` |
| **Label is optional** | Without it, reports say `profile 3` |
| **Exact spelling** | `NEXTDNS_API_KEY1` — one underscore, number at the end |

---

## 📩 Telegram (optional)

| Variable | Required | Example | Meaning |
|---|---|---|---|
| `TG_TOKEN` | — | `1234567890:AAHxxxx…` | bot token from BotFather |
| `TG_CHAT` | — | `123456789` | your Telegram user id |
| `TG_ON` | — | `true` / `false` | `false` disables all messages |

If `TG_TOKEN` **or** `TG_CHAT` is missing, no messages are sent (the sync is unaffected).

📖 [`06-TELEGRAM.md`](06-TELEGRAM.md)

---

## ⚙️ Tuning (optional — the defaults are fine)

| Variable | Default | Purpose |
|---|---|---|
| `SYNC_DELAY` | `10.0` | seconds to wait after each `POST` (rate-limit protection) |
| `SYNC_READ_DELAY` | `0.5` | seconds between reading two profiles |
| `SYNC_BACKFILL` | `true` | use bulk `PUT` when many items are missing |
| `SYNC_BULK_THRESHOLD` | `20` | how many items trigger a bulk `PUT` |
| `SYNC_RETRIES` | `4` | attempts per request before giving up |
| `SYNC_TIMEOUT` | `30` | HTTP timeout per request (seconds) |
| `SYNC_APPLY` | `true` | `false` = a hard read-only lock (nothing is ever written) |
| `SYNC_STATE_PATH` | `sync-state.json` | location of the state DB |
| `SYNC_SUMMARY_PATH` | `union-summary.json` | location of the run summary |

You do not need to set any of these. They exist so you can adjust behaviour without
touching the code.

---

## 🚫 Variables you do **not** need

- ❌ `GITHUB_TOKEN` — provided automatically by Actions
- ❌ `NEXTDNS_KEY` / `API_KEY` (without a number) — ignored
- ❌ profile names or fingerprints — the id is enough
- ❌ anything about device names, DoT, DoH — this tool only uses the NextDNS REST API

---

## 🔍 Verify your variables

### From Actions
The **"Check variables"** step prints a summary before the sync:

```
profiles found: 3 / 20
  [ 1] Home            id=ab12cd    key=...4567 (ok)
  [ 2] Phone           id=ef34gh    key=...cdef (ok)
  [ 3] Laptop          id=ij56kl    key=...ba98 (ok)

telegram: on - delay=10s - bulk>=20 - state=sync-state.json
```

Problems are listed explicitly, for example:

```
variables that need attention:
  ! profile 4 (TV): NEXTDNS_PROFILE_ID4 is empty
```

### Locally
```bash
python3 union.py --check     # are the variables complete?
python3 union.py --list      # ask NextDNS for the profile names (proves the keys work)
```

---

## 🔐 Security notes

| Item | Status |
|---|---|
| Keys inside the repository | ❌ none — they live in Variables |
| Safe to make the repo public | ✅ yes (no credentials are committed) |
| Key leaked? | NextDNS → Account → **API Key → Regenerate**, then update the variable |
| What a key can do | read/write **every profile in that account** — treat it like a password |
| What ends up in `sync-state.json` | profile ids and domains (no keys) |

> ⚠️ **`sync-state.json` contains your domains.** If you keep the repo public, everyone
> can read your allow/deny lists. That is a privacy choice, not a credential leak.
