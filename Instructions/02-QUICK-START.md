# 02 · Quick start (~10 minutes)

[⬅️ Back to index](README.md)

---

## ✅ What you need

| Requirement | Where |
|---|---|
| One or more NextDNS profiles | [my.nextdns.io](https://my.nextdns.io) |
| A NextDNS API key | [my.nextdns.io/account](https://my.nextdns.io/account) → bottom of the page |
| A GitHub repository | [github.com/new](https://github.com/new) |
| (optional) a Telegram bot | [@BotFather](https://t.me/BotFather) |

---

## Step 1 — Create the repository

```
GitHub → New repository
  Name: nextdns-profile-union        (any name)
  Visibility: Private                ← recommended, see the warning below
  ✅ Add a README file
  Create repository
```

> [!WARNING]
> **Use a private repository.** `sync-state.json` will contain the exact domains you
> allow and block, and the bot commits to it every run. The repo holds **no keys**, but
> a public repo would expose your lists and create a public commit every 12 hours.

---

## Step 2 — Find your profile id and API key

### Profile id
```
Open the profile in NextDNS and look at the URL:
   my.nextdns.io/ab12cd/settings
                ^^^^^^ this part
```

### API key
```
my.nextdns.io/account → scroll to the bottom
"API Key" → Show → copy
```

> 💡 One key can cover several profiles: a NextDNS account key grants access to every
> profile in that account, so the same key can be reused for slots 1–20.

---

## Step 3 — Add the variables

```
Repo → Settings → Secrets and variables → Actions → "Variables" tab
   ↓
New repository variable
```

**Minimum (2 variables):**

| Name | Value (example) |
|---|---|
| `NEXTDNS_API_KEY1` | `0123456789abcdef0123456789abcdef01234567` |
| `NEXTDNS_PROFILE_ID1` | `ab12cd` |

⛔ **Not the Secrets tab** — this project reads **Variables**.

More profiles:

| Name | Value |
|---|---|
| `NEXTDNS_API_KEY2` | `89abcdef…` |
| `NEXTDNS_PROFILE_ID2` | `ef34gh` |
| `NEXTDNS_API_KEY3` | `fedcba98…` |
| `NEXTDNS_PROFILE_ID3` | `ij56kl` |
| … up to 20 | … |

📖 Full reference → [`03-VARIABLES.md`](03-VARIABLES.md)

---

## Step 4 — Add the files

```
union.py
sync-state.json                       ← {"version":1,"profiles":{}}
.github/workflows/union-sync.yml      ⚠️ hidden folder
tests/test_union.py                   ← optional
Instructions/…                        ← optional
```

📖 Exact instructions (including the `.github` folder on Windows/mobile) →
[`04-INSTALL.md`](04-INSTALL.md)

---

## Step 5 — Allow the workflow to commit

```
Settings → Actions → General → Workflow permissions
   ◉ Read and write permissions
   Save
```

⚠️ Without this, `sync-state.json` is never committed and **every run re-adds the same
domains** (the state DB stays empty).

---

## Step 6 — First run (dry-run)

```
Actions → NextDNS profile union → Run workflow
   dry_run = true      ← inspect only
   full    = false
   Run workflow
```

⏱️ ~10–30 s. Open the run and read the **Job summary**:

```
=== allowlist ===
  read profile 1        22 entries
  read profile 2        12 entries
  union: 22 unique domains
  profile 1        up to date
  profile 2        +10 to add: ...
```

**Nothing was written** — this only shows what would happen.

---

## Step 7 — Apply

If the dry-run looks right:

```
dry_run = false
full    = false
Run workflow
```

⏱️ ~1–5 min (each `POST` waits 10 s; bulk `PUT`s do not).

---

## ✅ Done

From now on it runs every 12 hours by itself. Add a domain to any profile and the next
run propagates it everywhere.

---

## 🧭 Where to go next

| Need | File |
|---|---|
| All variables + examples | [`03-VARIABLES.md`](03-VARIABLES.md) |
| Telegram reports | [`06-TELEGRAM.md`](06-TELEGRAM.md) |
| Something broke | [`09-TROUBLESHOOTING.md`](09-TROUBLESHOOTING.md) |
| Questions | [`11-FAQ.md`](11-FAQ.md) |
| Making it public / forking | [`12-SECURITY.md`](12-SECURITY.md), [`13-TEMPLATE-GUIDE.md`](13-TEMPLATE-GUIDE.md) |
