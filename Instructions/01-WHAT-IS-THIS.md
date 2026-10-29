# 01 · What is this?

[⬅️ Back to index](README.md)

---

## In one sentence

> **A GitHub Action that links up to 20 NextDNS profiles: add a domain to one and it is automatically added to all the others.**

---

## What actually happens

```
        ┌─────────────┐
        │  Profile 1  │  ← you added "ads.example.com" here
        └──────┬──────┘
               │  (next scheduled run)
               ▼
     ┌─────────────────────────────┐
     │  UNION:  allowlist  22      │
     │          denylist  125      │
     └──────┬──────────┬────────┬──┘
            ▼          ▼        ▼
     ┌──────────┐ ┌──────────┐ ┌──────────┐
     │Profile 2 │ │Profile 3 │ │Profile 4 │   ← added everywhere
     └──────────┘ └──────────┘ └──────────┘
```

You only ever add the domain once.

---

## What is synced — and what is never touched

| ✅ Synced | ❌ Never touched |
|---|---|
| **allowlist** (domains you allow) | settings (logging, cache, Web3…) |
| **denylist** (domains you block) | security / privacy toggles |
| | blocklists (OISD, AdGuard…) |
| | parental control |
| | performance / analytics settings |
| | profile name, id, API key |

> 🧠 **Why:** syncing settings between profiles causes surprises (one profile wants
> logs, another must not have them). Restricting the tool to the two domain lists makes
> it safe to run unattended.

---

## Five properties that matter

### 1. Add-only
It **never** deletes an entry, never switches a toggle off and never flips
`active: false` to `true`. A bulk `PUT` resends the profile's existing entries together
with the new ones, so nothing can be lost.

### 2. Allowlist ≠ denylist
A domain in the allowlist never ends up in the denylist, and vice versa.
Covered by a test (`test_allow_and_deny_never_mix`).

### 3. No duplicates
`sync-state.json` in the repository remembers which domain was synced to which profile.
The same domain is never added twice.

### 4. Your manual deletes are respected
Delete a domain from one profile by hand and it will **not** come back: the state DB
remembers that it was synced there, so its absence means "the user removed it".
Need it back? See [`05-FULL-SYNC.md`](05-FULL-SYNC.md).

### 5. No credentials in the code
API keys, profile ids and the bot token are all **GitHub Variables**.
Nothing sensitive is committed, so the repository can be public.

---

## Who is this for

- People with several NextDNS profiles (phone, laptop, TV, family devices…)
- Anyone tired of copy-pasting the same domain into five profiles
- Anyone who wants one place to maintain a shared allow/deny list

---

## How a run works

```
1. GitHub Actions triggers (every 12 h, or manually)
2. Read allowlist + denylist from every profile   (GET)
3. Build the union of them
4. For every profile, add whatever it is missing
      - many items (20+)  → one bulk PUT
      - few items         → POST + 10 s cooldown
5. Save and commit sync-state.json
6. Send a Telegram report (optional)
```

---

## Next

- 🚀 Fastest path to a working setup → [`02-QUICK-START.md`](02-QUICK-START.md)
- 🔑 All variables → [`03-VARIABLES.md`](03-VARIABLES.md)
- 📄 Every file explained → [`07-FILES.md`](07-FILES.md)
