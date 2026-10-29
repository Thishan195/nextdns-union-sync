# 09 · Troubleshooting

[⬅️ Back to index](README.md)

**Start here:** open the run → **Job summary** (the tail of `sync.log`) or read the
Telegram message.

---

## A. The workflow never runs

| Symptom | Cause | Fix |
|---|---|---|
| No workflow in the **Actions** tab | `.github/workflows/union-sync.yml` is missing or in the wrong place | [`04-INSTALL.md`](04-INSTALL.md) — the folder is `.github` (with a dot) |
| It shows up but never runs | scheduled workflows must be enabled once | Actions → *NextDNS profile union* → **Enable workflow** |
| The schedule stops working after a while | GitHub disables schedules in repos with **60 days** of no activity | make a commit or trigger a manual run |
| The cron fires 5–20 minutes late | GitHub scheduler load | normal, expected |
| No **Run workflow** button | the workflow file is not on the default branch | merge it into `main` |
| Two runs at the same time | `concurrency` block removed | keep `concurrency:` in the file |

---

## B. Variables / profiles

| Log message | Cause | Fix |
|---|---|---|
| `No profile was found` | no variables set | add `NEXTDNS_API_KEY1` + `NEXTDNS_PROFILE_ID1` in the **Variables** tab |
| `profile 3 (Phone): NEXTDNS_PROFILE_ID3 is empty` | only the key was set | add the id, or remove both |
| `profiles found: 2 / 20` (fewer than expected) | slot numbers do not match | use the same number for key and id (`…_KEY5` + `…_ID5`) |
| `read Phone ERROR … 401` | the API key is wrong or was revoked | regenerate it at [my.nextdns.io/account](https://my.nextdns.io/account) |
| `read Phone ERROR … 404` | wrong profile id | copy the 6 characters from `my.nextdns.io/**xxxxxx**/settings` |
| `key=...???? (suspicious)` | the key looks too short | copy it again (no spaces or quotes) |
| Variables ignored | they were added under **Secrets** | move them to the **Variables** tab |

---

## C. Telegram

| Symptom | Cause | Fix |
|---|---|---|
| No message at all | `TG_TOKEN`/`TG_CHAT` missing or `TG_ON=false` | [`06-TELEGRAM.md`](06-TELEGRAM.md) |
| `! telegram failed … 400` | wrong `TG_CHAT` | send `/start` to the bot, read `getUpdates` |
| `! telegram failed … 401` | wrong or revoked token | BotFather → `/token` |
| `! telegram failed … 403` | the bot was blocked | send `/start` to the bot |
| `telegram message sent` but nothing arrives | the message went to another chat | re-check `TG_CHAT` |
| Bold text renders as plain text | the message was sent without `parse_mode` | update to the current `union.py` |

---

## D. Sync behaviour

| Log message | Cause | Action |
|---|---|---|
| `! domain.com skipped (HTTP 400 … duplicate)` | the profile already has that domain | normal — it is remembered and never retried |
| `! domain.com skipped (HTTP 500 / timeout)` | NextDNS or network hiccup | automatic retry on the next run |
| `BULK PUT … (verification FAILED -> falling back to POST)` | the write went through but the re-read did not show it | the fallback handles it; if it happens often set `SYNC_BACKFILL=false` |
| `bulk PUT failed (…) -> falling back to POST` | the bulk request was rejected | the fallback handles it; usually harmless |
| A manually deleted domain does not come back | correct behaviour (state memory) | see [`05-FULL-SYNC.md`](05-FULL-SYNC.md) |
| A manually deleted domain **does** come back | someone ran `full = true` | delete it again; it stays deleted after that |
| A domain is in both the allowlist and the denylist | it really is in both in NextDNS | clean it up by hand; the tool keeps each list as-is |
| `union: 0 unique domains` | every profile is empty | normal on a fresh setup |
| A new domain was not synced | the run happened before you added it | wait for the next run or dispatch one manually |

---

## E. State DB / commit

| Symptom | Cause | Fix |
|---|---|---|
| `Commit state DB` fails with **403** | Actions cannot write to the repo | **Settings → Actions → General → Workflow permissions → "Read and write"** → Save |
| `protected branch hook declined` | `main` is protected | allow the bot to push, or push to another branch |
| `sync-state.json` is never committed | it is listed in `.gitignore` | remove that line |
| **Every run re-adds the same domains** | the state DB is never committed | fix the 403 above |
| `cannot read the state file` | invalid JSON | reset it to `{"version":1,"profiles":{}}` |
| Domains stored as `[a.com](http://a.com)` | the file was mangled by markdown | reset it; the next run rebuilds it |

---

## F. Timing / limits

| Symptom | Cause | Fix |
|---|---|---|
| The `Union sync` step takes ~3 minutes | 10 s cooldown per `POST` | expected behaviour |
| Cancelled after **90 min** | very large lists across many profiles | lower `SYNC_BULK_THRESHOLD` (e.g. `5`) or raise `timeout-minutes` |
| Runs twice every 12 hours | another workflow is also scheduled | check the Actions tab |

---

## G. Running locally

| Error | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError` | running from the wrong directory | `cd` into the folder that contains `union.py` |
| `No profile was found` | variables not exported | `export NEXTDNS_API_KEY1=…` |
| `403` from NextDNS | missing `User-Agent` | keep the `UA` constant in `union.py` |
| `429` | too many requests too fast | raise `SYNC_DELAY` (e.g. `15`) |

---

## 🆘 Nothing works — reset and start again

```
1. sync-state.json  →  {"version":1,"profiles":{}}
2. Actions → Run workflow → dry_run = true   → read what it would do
3. dry_run = false                           → apply
4. Still failing? read the Telegram message or the Job summary
```

> 🧠 Always preview with `dry_run = true`. It writes nothing, so there is no risk.
