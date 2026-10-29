# 05 · `full` — the emergency switch

[⬅️ Back to index](README.md)

> Everything about **`full = true`** (or `python3 union.py --full`).
> A normal run never needs it.

---

## 1. What `full` means

> **`full = true` forgets the memory inside `sync-state.json` and writes every domain of
> the union to every profile again.**

| | `full = false` (normal) | `full = true` (emergency) |
|---|---|---|
| Reads `sync-state.json`? | ✅ yes | ❌ ignored |
| What gets written | only the **missing** domains | **every** domain |
| A domain you deleted by hand | stays deleted ✅ | **comes back** ⚠️ |
| Requests | few | more (still ~4–8 thanks to bulk `PUT`) |
| Duration | ~5 s – 3 min | ~1 – 5 min |
| Risk | 🟢 low | 🟠 real |

---

## 2. ✅ When you *should* use `full = true`

### (A) You deleted a domain by hand and want it back
```
You removed a domain from one profile
   ↓
The state DB remembers it, so it is never re-added (correct behaviour ✅)
   ↓
But now you want it again  →  full = true
```

### (B) `sync-state.json` got corrupted
- invalid JSON
- domains turned into markdown links like `[api.cloudflare.com](http://api.cloudflare.com)`
- the file was deleted or truncated

**Preferred fix:** reset the file to `{"version":1,"profiles":{}}` and do a **normal**
run — it rebuilds itself. Use `full` only when you also want the "deleted by hand"
memory cleared.

### (C) You want `active: false` entries switched back on
A bulk write re-adds the domain as active. Note that it becomes active in **every**
profile, because the union marks a domain active when it is active anywhere.

### (D) A profile needs a complete rebuild
Usually unnecessary: a brand-new profile is filled by a normal run.

---

## 3. ❌ When you must **not** use `full = true`

| Situation | Why it hurts |
|---|---|
| You deliberately deleted a domain | it is resurrected |
| You moved a domain from denylist to allowlist | it may be re-added to the denylist too |
| Everything already works | wasted requests and the memory is reset |
| "Something feels wrong, let me try" | run `dry_run = true` first — it writes nothing |
| You added a new profile | a normal run fills it automatically |

> 🧠 **`full` resets the only memory that encodes "I deleted this on purpose".**

---

## 4. 🛡️ Use it safely

```
Step 1:  dry_run = true  +  full = true     ← preview, writes nothing
             ↓  read the Job summary / Telegram message ("would write")
Step 2:  dry_run = false +  full = true     ← apply
             ↓
Step 3:  back to normal (dry_run = false, full = false)   ← don't forget
```

> 💡 Scheduled runs never receive `full` — it only applies to manual dispatch.

---

## 5. What happens inside a `full` run

```
1. read every profile
2. build the union (allowlist and denylist separately — never mixed)
3. for each profile: ignore the state DB, add every union domain it is missing
4. 20+ items → bulk PUT · fewer → POST + 10 s cooldown
5. write a fresh state DB
```

⚠️ Still add-only: nothing is deleted by `full`.

---

## 6. Making a domain stay deleted after a `full` run

```
1. Delete it in NextDNS
2. The next run sees it in the fresh state DB and skips it
```

---

## 7. Spotting a `full` run in Telegram

```
🔍 NextDNS profile union - DRY-RUN     ← dry_run = true
✅ NextDNS profile union               ← normal
✅ NextDNS profile union - FULL        ← you ran with full = true
```

If you see `- FULL` and did not mean it, set `full = false`.

---

## 8. Checklist

```
☐ Why do I need full?  →  "I deleted something on purpose and want it back"
                          or "the state DB is broken"
☐ Did I preview with dry_run = true + full = true?
☐ Am I comfortable with the domains that will return?
☐ Did I switch full back to false afterwards?      ← important
```

---

## 9. Alternatives that do not need `full`

| Goal | Without `full` |
|---|---|
| Re-add a single domain | ✅ add it to **another** profile by hand — the next run propagates it (it is not in the state DB) |
| Rebuild the state DB | ✅ set it to `{"version":1,"profiles":{}}` |
| Re-write everything | ❌ only `full` does this |

> 🌚 Most "I need that domain back" cases are solved by adding it to one profile.
