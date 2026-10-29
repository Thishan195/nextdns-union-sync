# 12 · Security

[⬅️ Back to index](README.md)

---

## ✅ Short answer

> **No API keys and no bot tokens are committed.** They live in GitHub **Variables**
> (repository settings), never in the code, so the repository itself can be public.

---

## 🔍 What is in the repository

| File | Contents | Visible when public |
|---|---|---|
| `union.py` | code only — **no keys** | ✅ fine |
| `sync-state.json` | profile ids + **domains** | ⚠️ visible — see below |
| `.github/workflows/union-sync.yml` | `toJson(vars)` — **no values** | ✅ fine |
| `README.md`, `Instructions/` | documentation (placeholders only) | ✅ fine |
| `tests/test_union.py` | tests with fake data | ✅ fine |

### Credentials checklist

```
API keys      → GitHub Variables only   ❌ not in the code
Bot token     → GitHub Variables only   ❌ not in the code
Profile ids   → Variables + sync-state.json
```

The workflow only ever contains:

```yaml
env:
  ALL_VARS: ${{ toJson(vars) }}    # filled at runtime, never printed by the script
```

---

## ⚠️ The real considerations when going public

### 1. `sync-state.json` shows your domains
```json
"denylist": ["ads.tiktok.com", "x.com", "..."]
```
It reveals which domains you allow and block, plus your profile ids (which alone cannot
be used without an API key).

**Options:**
- ✅ Keep the repo **private** (simplest and recommended)
- ✅ Stay public if you do not mind those lists being readable
- ⚙️ Advanced: set `SYNC_STATE_PATH` to a file outside the repo, or hash the profile ids
  in the code — both require small code changes

### 2. Git history
⚠️ If you **ever** committed a key in an earlier version, editing the file does **not**
remove it from history.

**Fix:** create a fresh repository and push the current files only:
```bash
git clone --depth 1 https://github.com/USER/REPO.git fresh
cd fresh && rm -rf .git && git init && git add . && git commit -m "init"
```
And **regenerate** any key that was ever committed (NextDNS → Account → API Key).

### 3. Local `.env` files
Avoid them; use `export`. If you must, keep them in `.gitignore`:

```
.env
*.log
__pycache__/
```

### 4. Forks keep the bot token
Anyone who forks the repository inherits the **file contents**, not your Variables.
However, if a fork was made from a commit that contained a token, the fork keeps that
token in its history.

---

## 🛡️ Good practice

| ✅ Do | ❌ Don't |
|---|---|
| Keep keys in **Variables** | hardcode keys in `union.py` |
| Prefer a **private** repo | commit `.env` files |
| **Regenerate** a leaked key | keep using it |
| Set `Workflow permissions` to **Read and write** only | grant admin scopes |
| Review forks before running them | hand your Variables to unknown forks |

### Workflow permissions

```yaml
permissions:
  contents: write      # only what is needed to commit the state DB
```

Everything else (issues, packages, pull-requests, actions) is denied by default.

### Third-party actions

```yaml
uses: actions/checkout@v4          # GitHub official
uses: actions/setup-python@v5      # GitHub official
uses: actions/upload-artifact@v4   # GitHub official
```

**GitHub-official actions only** — no supply-chain risk from random actions.

---

## 🔐 What a NextDNS API key can do

NextDNS keys are **account-level**:

| Can | Cannot |
|---|---|
| ✅ read/write **every profile in the account** | ❌ create new profiles (needs a login) |
| ✅ modify allowlists, denylists, settings | ❌ change the account password |
| ✅ delete profiles | ❌ see billing or payment details |
| | ❌ touch other accounts |

⚠️ Treat it like a password and regenerate it if it is ever exposed.

---

## 🧪 Verify it yourself

```bash
# any 40-character hex strings (API keys)?
grep -rE "[0-9a-f]{40}" . --exclude-dir=.git
# expected: nothing (or fake values inside documentation examples)

# any bot tokens?
grep -rn "AAH" . --exclude-dir=.git
# expected: nothing

# where is the key used?
grep -rn "X-Api-Key" union.py
# expected: the header name only, never a value
```

---

## 📋 Public repo checklist

```
☐ No API keys anywhere in the code            ✅ Variables
☐ No bot token in the code                    ✅ Variables
☐ Git history is clean too                    ⚠️ verify (fresh repo if unsure)
☐ I know sync-state.json exposes my domains   ⚠️ accepted
☐ permissions: contents: write only           ✅
☐ No third-party actions                      ✅
☐ .gitignore contains .env and *.log          ✅
```

> 🌚 **Simplest advice:** if you want zero doubt, keep the repository private.
> It can be public — but it does not have to be.
