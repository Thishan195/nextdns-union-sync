# 08 · How it works

[⬅️ Back to index](README.md)

> Read this if you want to understand a bug, change the code, or fork it seriously.
> Normal use does not require any of it.

---

## 1. Full flow

```
┌──────────────────────────────────────────────────────────────┐
│  GitHub Actions (every 12 h, or manual dispatch)             │
└───────────────────────────┬──────────────────────────────────┘
                            ▼
              ┌──────────────────────────┐
              │ 1. read variables        │  ALL_VARS (JSON)
              │    load_profiles()       │  NEXTDNS_API_KEY1..20
              └────────────┬─────────────┘  NEXTDNS_PROFILE_ID1..20
                           ▼
              ┌──────────────────────────┐
              │ 2. read the state DB     │  sync-state.json
              │    load_state()          │
              └────────────┬─────────────┘
                           ▼
        ┌──────────────────┴──────────────────┐
        │   for each list (allowlist, denylist) │
        └──────────────────┬──────────────────┘
                           ▼
              ┌──────────────────────────┐
              │ 3. read the list from     │  GET /profiles/:id/:list
              │    every profile          │  (with pagination)
              └────────────┬─────────────┘
                           ▼
              ┌──────────────────────────┐
              │ 4. build the union        │  union[domain] = active
              │                          │  (active if active anywhere)
              └────────────┬─────────────┘
                           ▼
        ┌──────────────────┴──────────────────┐
        │  5. for every profile (separately)    │
        └──────────────────┬──────────────────┘
                           ▼
        ┌─────────────────────────────────────┐
        │ todo = union - what the profile has  │
        │              - what the state knows  │
        └──────────────────┬──────────────────┘
                           ▼
              ┌────────────┴────────────┐
              ▼                         ▼
     todo >= 20 (bulk)          todo < 20 (POST)
     ┌──────────────┐          ┌──────────────┐
     │ GET again     │          │ POST one by  │
     │ + append      │          │ one, 10 s    │
     │ PUT (1 call)  │          │ cooldown     │
     │ GET to verify │          │ skip errors  │
     └──────────────┘          └──────────────┘
              │                         │
              └────────────┬────────────┘
                           ▼
              ┌──────────────────────────┐
              │ 6. save + commit the DB  │
              └────────────┬─────────────┘
                           ▼
              ┌──────────────────────────┐
              │ 7. Telegram report       │
              └──────────────────────────┘
```

---

## 2. Building the union

```python
union: dict[str, bool] = {}
for entries in per_profile.values():
    for domain, active in entries.items():
        union[domain] = union.get(domain, False) or active
```

A domain is **active** in the union if it is active in **at least one** profile.
If it is inactive everywhere it is still part of the union (as `active: false`), so it
gets added switched-off rather than skipped.

---

## 3. Computing `todo` — the heart of the logic

```python
for domain in sorted(union):
    if domain in have:                    # ① the profile already has it
        continue
    if not full and domain in already:    # ② the state DB remembers it
        skipped += 1
        continue                          #    → user deleted it on purpose
    todo.append((domain, union[domain]))  # ③ add it
```

| Situation | ① live list | ② state DB | Result |
|---|---|---|---|
| brand-new domain | ❌ | ❌ | ✅ added |
| already present | ✅ | ✅ | ⏭ skipped (no duplicate) |
| deleted by hand | ❌ | ✅ | ⏭ skipped (respected) |
| `full = true` | ❌ | ✅ | ✅ added (memory ignored) |

---

## 4. The `seeded` flag — a real bug that this prevents

```python
if not is_seeded(state, p["id"], kind):
    remember(state, p["id"], kind, have.keys())
    mark_seeded(state, p["id"], kind)
    already = seen_domains(state, p["id"], kind)   # re-read after marking
```

### 💀 Trap 1 — a single global "is this the first run?" check

An earlier version did:

```python
seeding = all(not seen_domains(state, p["id"], kind) for p in PROFILES)   # wrong
```

This was evaluated **once**, before the loop. As soon as the first profile was seeded,
the state DB was no longer empty, so **every remaining profile looked "already seeded"**
and was never filled. Empty profiles stayed empty forever.

### 💀 Trap 2 — an empty list is not "not seeded"

If a list is empty, `not seen_domains(...)` is `True`, so the profile was treated as a
first run on **every** run — and therefore never synced.

### ✅ The fix

A per-profile, per-list `seeded` flag: "this list has been read at least once", even when
it was empty.

> 🧪 Covered by `test_empty_profile_is_filled_on_the_very_first_run`.

---

## 5. Bulk `PUT` vs `POST`

### POST (fewer than 20 items)
```
POST /profiles/:id/allowlist  {"id": "a.com", "active": true}
   ↓ wait 10 s
POST /profiles/:id/allowlist  {"id": "b.com", "active": true}
   ↓ ...
```
125 domains ≈ 21 minutes. Slow but gentle.

### Bulk PUT (20 items or more)
```
GET  /profiles/:id/allowlist        ← existing entries
   ↓
entries = existing + new
   ↓
PUT  /profiles/:id/allowlist  [ ... ]   ← one request
   ↓
GET  /profiles/:id/allowlist        ← verify
```
125 domains ≈ 2 seconds.

### Why `PUT` is safe here

`PUT` replaces the whole list, so the code re-reads it first and sends everything back:

```python
entries = [dict(e) for e in get_list(...)]      # ① keep what exists
existing = {e["id"].lower() for e in entries}
for domain, active in todo:
    if domain not in existing:                  # ② never duplicate
        entries.append({"id": domain, "active": active})
request("PUT", ..., body=entries)               # ③ existing + new
after = get_list(...)                           # ④ verify
```

Nothing is lost, `active` flags are preserved, and if the write or the verification
fails the code falls back to `POST` one by one.

---

## 6. Error handling — a run never dies

| Error | Behaviour |
|---|---|
| `400 duplicate / already exists` | skipped **and remembered** in the state DB (never retried) |
| `500 / 502 / timeout` | 4 attempts with backoff, then skipped and **retried on the next run** |
| `429 rate limit` | sleeps 15–80 s, then retries |
| a profile cannot be read | that profile is skipped, the others continue |
| bulk `PUT` fails | falls back to `POST` |
| Telegram fails | 3 attempts, then silently gives up |
| the script crashes | `run_guarded()` sends the traceback to Telegram |

### The important distinction

| Error type | Written to the state DB? | Next run |
|---|---|---|
| duplicate (400) | ✅ yes | not retried |
| 500 / network | ❌ no | retried |
| read failure | ❌ no | retried |

Duplicate means "it is already there" (retrying is pointless). 500 means "it never
arrived" (retrying is required).

---

## 7. How the state file is written

```python
state["profiles"] = {
    pid: {k: sorted(set(v)) for k, v in sorted(lists.items()) if v}
    for pid, lists in sorted(state["profiles"].items())
}
```

- `sorted()` keeps the git diff stable (no churn when nothing changed)
- `set()` removes duplicates
- `if v` drops empty lists, keeping the file small

---

## 8. How the Telegram report is built

- HTML parse mode (`<b>`, `<code>`, `<i>`, `<pre>`)
- `tg_esc()` escapes `&`, `<`, `>` so a domain containing `&` cannot break the message
- a `400` response triggers a retry **without** `parse_mode` (plain-text fallback)

---

## 9. Writing a test

`tests/test_union.py` ships a fake API:

```python
def test_my_new_case():
    with tempfile.TemporaryDirectory() as d:
        profiles = setup(d)                 # fake DB, profiles, state path
        run_all(profiles)                   # seed
        DB["p1"]["denylist"].append({"id": "new.com", "active": True})
        run_all(profiles)                   # sync
        for pid in DB:
            assert "new.com" in {e["id"] for e in DB[pid]["denylist"]}, pid
```

Available helpers:

| Helper | Purpose |
|---|---|
| `DB` | fake NextDNS data |
| `WRITES` | recorded requests, e.g. `("POST", "p1", "allowlist", {...})` |
| `FAIL_POSTS` / `FAIL_POSTS_500` / `FAIL_READS` | simulate errors |
| `run_all(profiles, apply=False)` | dry-run |

```bash
python3 tests/test_union.py
```

---

## 10. Adding another NextDNS list ⚠️

**Don't.** `LISTS = ("allowlist", "denylist")` is intentional.

`sync_kind()` assumes a NextDNS *domain list* endpoint (array of `{id, active}`).
Settings, security and privacy endpoints have a completely different shape and would
need separate logic — plus syncing settings between profiles creates surprises.

If you truly need more, write a separate function and call it from `main()`; do not add
it to `LISTS`.
