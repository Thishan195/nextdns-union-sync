# 13 · Using this as a public template

[⬅️ Back to index](README.md)

> This project is meant to be shared: **the template stays public, your copy stays private.**

---

## 🗂️ The two repositories

```
┌───────────────────────────────┐        ┌───────────────────────────────┐
│  TEMPLATE (public)            │        │  YOUR COPY (private) ⭐        │
│                               │  fork  │                               │
│  no keys                      │ ─────► │  no keys (same code)          │
│  sync-state.json empty        │        │  sync-state.json → YOUR data  │
│  safe to show to everyone     │        │  only you can see it          │
└───────────────────────────────┘        └───────────────────────────────┘
        ▲                                         │
        │  updates (new version)                  │  every run commits here
        └─────────────────────────────────────────┘
```

| Repository | Visibility | Contains |
|---|---|---|
| Template (this one) | **public** | code + docs, empty state DB, no credentials |
| Your fork | **private** ⭐ | the same code + **your** domains, profile ids and commit history |

---

## 🍴 How to fork into a private repo

### Option A — fork, then make it private (easiest)
```
1. Click "Fork" on the template
2. In the "Create a new fork" screen choose Owner: yourself
3. Create
4. Settings → General → Danger Zone → Change repository visibility → Private → confirm
```

### Option B — import without forking
```
1. github.com/new/import
2. Paste the template URL
3. Name it, choose Private
```

### Option C — clone and push (keeps history out)
```bash
git clone --depth 1 https://github.com/TEMPLATE-OWNER/nextdns-profile-union.git my-union
cd my-union
rm -rf .git
git init
git add .
git commit -m "init"
git remote add origin https://github.com/YOU/my-union.git
git push -u origin main
```

> ⚠️ **Why private?** `sync-state.json` contains the exact domains you allow and block,
> and the bot commits to it every 12 hours. In a public fork both your lists and your
> commit history become public.

---

## 🔧 After forking — the 5-minute setup

```
1. Settings → Secrets and variables → Actions → Variables
      NEXTDNS_API_KEY1      = <your key>
      NEXTDNS_PROFILE_ID1   = <your profile id>
      NEXTDNS_LABEL1        = Home            (optional)

2. Settings → Actions → General → Workflow permissions
      ◉ Read and write permissions  → Save

3. sync-state.json → keep it as {"version":1,"profiles":{}}  (do not copy data from the template)

4. Actions → NextDNS profile union → Run workflow
      dry_run = true  → review
      dry_run = false → apply
```

Done. The template's files and your data never mix.

---

## 🔄 Getting updates later

There is no auto-merge — and that is intentional: a merge could overwrite your state DB.

```bash
# inside your private repo
git remote add upstream https://github.com/TEMPLATE-OWNER/nextdns-profile-union.git
git fetch upstream
git checkout -b template-update upstream/main

# bring the updated files over by hand (recommended: union.py and the workflow only)
git checkout main
git checkout template-update -- union.py .github/workflows/union-sync.yml Instructions/
git commit -m "update from template"
git push
```

| File | Safe to update | Note |
|---|---|---|
| `union.py` | ✅ | the main logic |
| `.github/workflows/union-sync.yml` | ✅ | check the cron and permissions afterwards |
| `Instructions/`, `README.md` | ✅ | docs |
| `sync-state.json` | ❌ **never** | this is your data |
| `.gitignore`, `LICENSE` | ✅ | rarely change |

> 💡 Simplest safe approach: update `union.py` + the workflow, run the tests
> (`python3 tests/test_union.py`), then dispatch a `dry_run = true` run.

---

## 🤝 Contributing back

If you improve something you want everyone to have:

1. Change it in **your private repo** first and test it
2. Copy only the generic part (no keys, no domains, no profile ids) into a branch of the template
3. Verify `python3 tests/test_union.py` passes and `grep -rE "[0-9a-f]{40}" .` finds nothing
4. Open a pull request

⚠️ **Never paste your `sync-state.json`, API keys or bot token into a pull request.**

---

## 📋 Template checklist (before you share it)

```
☐ No keys / tokens anywhere      grep -rE "[0-9a-f]{40}|AAH" . --exclude-dir=.git
☐ sync-state.json is empty       {"version":1,"profiles":{}}
☐ README has the fork → private warning
☐ Tests pass                     python3 tests/test_union.py
☐ A logged-out reader can finish the setup from Instructions/ alone
```
