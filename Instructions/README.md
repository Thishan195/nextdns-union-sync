# 📚 Instructions

Documentation for **NextDNS Profile Union**. Each topic has its own file so you can
find things quickly instead of scrolling one huge page.

---

## 🚀 Start here

| # | File | What it covers | Read it if… |
|---|---|---|---|
| 1 | [`01-WHAT-IS-THIS.md`](01-WHAT-IS-THIS.md) | What this is, what is (and is not) synced | you are new |
| 2 | [`02-QUICK-START.md`](02-QUICK-START.md) | Working setup in ~10 minutes | you want it running now |

## 📖 Reference

| # | File | What it covers |
|---|---|---|
| 3 | [`03-VARIABLES.md`](03-VARIABLES.md) | Every variable, with examples (profiles 1–20) |
| 4 | [`04-INSTALL.md`](04-INSTALL.md) | Where each file goes, including the `.github` folder |
| 5 | [`05-FULL-SYNC.md`](05-FULL-SYNC.md) | `full = true` — when you need it and when you must not |
| 6 | [`06-TELEGRAM.md`](06-TELEGRAM.md) | Create a bot and get reports on your phone |
| 7 | [`07-FILES.md`](07-FILES.md) | What every file does + the state DB schema |

## 🔧 Deep dives

| # | File | What it covers |
|---|---|---|
| 8 | [`08-HOW-IT-WORKS.md`](08-HOW-IT-WORKS.md) | The logic, the union rule, bulk PUT, error handling, known traps |
| 9 | [`09-TROUBLESHOOTING.md`](09-TROUBLESHOOTING.md) | 40+ errors → cause → fix (sections A–G) |
| 10 | [`10-COMMANDS.md`](10-COMMANDS.md) | Local commands, curl examples, inspecting the state DB |
| 11 | [`11-FAQ.md`](11-FAQ.md) | 32 questions and answers |
| 12 | [`12-SECURITY.md`](12-SECURITY.md) | Public repo safety, keys, permissions, forks |

> 📄 `13-TEMPLATE-GUIDE.md` explains the two repos you end up with when you use this
> as a public template (the template and your own private fork).

---

## 🎯 Find it fast

| I want to… | Open |
|---|---|
| set it up for the first time | [`02-QUICK-START.md`](02-QUICK-START.md) |
| add my API keys / profile ids | [`03-VARIABLES.md`](03-VARIABLES.md) |
| find the `.github` folder | [`04-INSTALL.md`](04-INSTALL.md) |
| understand `full` | [`05-FULL-SYNC.md`](05-FULL-SYNC.md) |
| get notifications on my phone | [`06-TELEGRAM.md`](06-TELEGRAM.md) |
| fix an error | [`09-TROUBLESHOOTING.md`](09-TROUBLESHOOTING.md) |
| make the repo public safely | [`12-SECURITY.md`](12-SECURITY.md) |
| fork this template correctly | [`13-TEMPLATE-GUIDE.md`](13-TEMPLATE-GUIDE.md) |

---

## ⚡ Cheat sheet

```
Variables  (Settings → Secrets and variables → Actions → Variables)
  NEXTDNS_API_KEY1      = <api key>        required
  NEXTDNS_PROFILE_ID1   = <profile id>     required
  NEXTDNS_LABEL1        = Phone            optional
  ... repeat up to 20

  TG_TOKEN              = <bot token>      optional
  TG_CHAT               = <user id>        optional
  TG_ON                 = true             optional

Files
  union.py                               root
  sync-state.json                        root   {"version":1,"profiles":{}}
  .github/workflows/union-sync.yml       ⚠️ hidden folder

Settings
  Actions → General → Workflow permissions = Read and write

Run
  Actions → NextDNS profile union → Run workflow
    dry_run = true    → inspect
    dry_run = false   → apply
```

---

## 🤖 What it does

```
You add "ads.example.com" to profile 1
        ↓   (next run, every 12 h)
the union of allowlist + denylist is calculated
        ↓
the domain is added to profiles 2 … 20
        ↓
nothing deleted · nothing switched off · no duplicates · allow ≠ deny
```
