# 04 · Install — where every file goes

[⬅️ Back to index](README.md)

---

## 📁 Final folder layout

```
repo-root/
├── union.py                              ⭐ main script
├── sync-state.json                       ⭐ the state DB (empty to start)
├── union-sync.yml                        convenience copy of the workflow
├── README.md
├── LICENSE
├── .gitignore
├── .github/
│   └── workflows/
│       └── union-sync.yml                ⭐ ⚠️ HIDDEN folder
├── Instructions/
│   ├── README.md
│   ├── 01-WHAT-IS-THIS.md
│   ├── 02-QUICK-START.md
│   ├── 03-VARIABLES.md
│   ├── 04-INSTALL.md
│   ├── 05-FULL-SYNC.md
│   ├── 06-TELEGRAM.md
│   ├── 07-FILES.md
│   ├── 08-HOW-IT-WORKS.md
│   ├── 09-TROUBLESHOOTING.md
│   ├── 10-COMMANDS.md
│   ├── 11-FAQ.md
│   ├── 12-SECURITY.md
│   └── 13-TEMPLATE-GUIDE.md
└── tests/
    └── test_union.py                     optional
```

**⭐ = required. Everything else is optional.**

---

## ⚠️ The one thing that trips everyone up: `.github/workflows/`

GitHub Actions reads workflows from **exactly one place**:

```
.github/workflows/union-sync.yml
```

The folder name starts with a **dot**. Windows Explorer, several ZIP tools and most
mobile file managers hide dot-folders or skip them on extraction.

### ✅ Correct
```
repo/.github/workflows/union-sync.yml
```

### ❌ Wrong (the workflow never runs)
```
repo/github/workflows/union-sync.yml      ← dot missing
repo/.github/union-sync.yml               ← "workflows" missing
repo/union-sync.yml                       ← root of the repo
```

---

## 🪟 Windows — creating `.github`

### Option 1 — Explorer
1. Open the repo folder
2. `New folder` → name it `.github` (dot first, **no** trailing dot)
3. If Windows refuses, name it `.github.` and press Enter — Windows strips the last dot
4. Inside it create `workflows`
5. Copy `union-sync.yml` into `workflows`

### Option 2 — Command Prompt (fastest)
```cmd
cd path\to\your\repo
mkdir .github\workflows
copy union-sync.yml .github\workflows\union-sync.yml
```

### Option 3 — PowerShell
```powershell
New-Item -ItemType Directory -Force -Path .github\workflows
Copy-Item union-sync.yml .github\workflows\
```

### Option 4 — reveal hidden items
`View → Show → Hidden items` — then you can see `.github` normally.

---

## 📱 Mobile / phone

### ✅ Option A — GitHub web, `Add file → Create new file`
```
1. Repo → Add file → Create new file
2. Type the full path in the file-name box:

   .github/workflows/union-sync.yml

   or open this URL directly:
   github.com/USER/REPO/new/main?filename=.github/workflows/union-sync.yml
```
Typing `/` creates the folders automatically.

### ✅ Option B — do it once on a computer
Once the file exists you can edit it from your phone forever.

### ✅ Option C — use the root `union-sync.yml`
The ZIP contains a plain `union-sync.yml` at the root. It is **not** executed by GitHub;
it exists purely so you always have the content available to copy into
`.github/workflows/union-sync.yml`.

---

## 📄 `sync-state.json`

```json
{
  "version": 1,
  "updated": null,
  "profiles": {}
}
```

| Question | Answer |
|---|---|
| Should I add it? | ✅ nice to have, but **not required** — the script creates it if missing |
| Should I edit `profiles`? | ❌ never |
| Can I edit it by hand? | ❌ don't — a JSON syntax error wipes the memory |
| Can I delete it? | ✅ the next run recreates it (you lose the "already synced / user deleted" memory) |
| Where does it go? | repo root |

---

## 🔧 `.gitignore`

```
__pycache__/
*.pyc
sync.log
union-summary.json
.env
```

⚠️ **Never add `sync-state.json`** — if it is ignored it is never committed, and every
run will re-add the same domains.

---

## ✅ Install checklist

```
☐ union.py                                 (root)
☐ sync-state.json                          (root, {"version":1,"profiles":{}})
☐ .github/workflows/union-sync.yml         ← verify the path!
☐ Variables: NEXTDNS_API_KEY1 + NEXTDNS_PROFILE_ID1
☐ Settings → Actions → General → Workflow permissions = Read and write
☐ Actions tab → Enable workflows (first time only)
☐ Run workflow → dry_run = true  → inspect
☐ Run workflow → dry_run = false → apply
```

---

## 🧪 Verify without running the workflow

```bash
python3 union.py --check      # variables parsed correctly?
python3 union.py --list       # do the keys really work?
python3 tests/test_union.py   # 25 offline tests
```
