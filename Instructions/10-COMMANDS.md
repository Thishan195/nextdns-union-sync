# 10 · Commands

[⬅️ Back to index](README.md)

> Not required — Actions does everything. Useful for debugging and quick checks.

---

## 1. Setup (once)

```bash
python3 --version         # 3.9 or newer

cd nextdns-profile-union

export NEXTDNS_API_KEY1="0123456789abcdef0123456789abcdef01234567"
export NEXTDNS_PROFILE_ID1="ab12cd"
export NEXTDNS_LABEL1="Home"

export NEXTDNS_API_KEY2="89abcdef0123456789abcdef0123456789abcdef"
export NEXTDNS_PROFILE_ID2="ef34gh"
export NEXTDNS_LABEL2="Phone"

# optional
export TG_TOKEN="1234567890:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export TG_CHAT="123456789"
export SYNC_DELAY=10
```

Windows: `set NAME=value` (cmd) or `$env:NAME="value"` (PowerShell).

---

## 2. All commands

| Command | What it does | Writes? |
|---|---|---|
| `python3 union.py --check` | validate the variables | ❌ |
| `python3 union.py --list` | ask NextDNS for profile names (proves the keys work) | ❌ |
| `python3 union.py --dry-run` | show what would be added | ❌ |
| `python3 union.py` | apply | ✅ |
| `python3 union.py --full` | ignore the state DB | ✅ |
| `python3 union.py --no-notify` | skip Telegram | per other flags |
| `python3 union.py --dry-run --full` | preview a `full` run | ❌ |
| `python3 tests/test_union.py` | 25 offline tests | ❌ |

---

## 3. Examples

### Validate the variables
```bash
python3 union.py --check
```
```
profiles found: 2 / 20
  [ 1] Home            id=ab12cd    key=...4567 (ok)
  [ 2] Phone           id=ef34gh    key=...cdef (ok)

telegram: on - delay=10s - bulk>=20 - state=sync-state.json
```

### Prove the keys work
```bash
python3 union.py --list
```
```
profiles:
  [ 1] Home            id=ab12cd    -> 'Home'
  [ 2] Phone           id=ef34gh    -> 'My phone'
```
An `ERROR` here means a wrong key or id.

### Preview
```bash
python3 union.py --dry-run
```
```
=== allowlist ===
  read Home            22 entries
  read Phone           12 entries
  union: 22 unique domains
  Home             up to date
  Phone            +10 to add: catbox.moe, playmods.net, ...

DRY-RUN finished (nothing written)
```

### Apply
```bash
python3 union.py
```
```
  Phone            +1 to add: x.com
      + x.com  (1 written, 10s cooldown)
DONE
```

### Locally without Telegram
```bash
python3 union.py --no-notify
```

### Tests
```bash
python3 tests/test_union.py
```

---

## 4. Talking to the API directly (curl)

### List the profiles of a key
```bash
curl -s -H "X-Api-Key: $NEXTDNS_API_KEY1" -H "User-Agent: curl/8.0" \
     https://api.nextdns.io/profiles
```

### One profile
```bash
curl -s -H "X-Api-Key: $NEXTDNS_API_KEY1" -H "User-Agent: curl/8.0" \
     https://api.nextdns.io/profiles/ab12cd
```

### The allowlist
```bash
curl -s -H "X-Api-Key: $NEXTDNS_API_KEY1" -H "User-Agent: curl/8.0" \
     https://api.nextdns.io/profiles/ab12cd/allowlist | python3 -m json.tool
```

### Just the number of deny entries
```bash
curl -s -H "X-Api-Key: $NEXTDNS_API_KEY1" -H "User-Agent: curl/8.0" \
     https://api.nextdns.io/profiles/ab12cd/denylist \
  | python3 -c "import json,sys; print(len(json.load(sys.stdin)['data']))"
```

### Add one domain by hand
```bash
curl -s -X POST -H "X-Api-Key: $NEXTDNS_API_KEY1" -H "User-Agent: curl/8.0" \
     -H "Content-Type: application/json" \
     -d '{"id":"example.com","active":true}' \
     https://api.nextdns.io/profiles/ab12cd/denylist
```

⚠️ The `User-Agent` header is required — Cloudflare answers `403` without it.

---

## 5. Inspecting the state DB

### Per-profile counts
```bash
python3 -c "
import json
s = json.load(open('sync-state.json'))
for pid, d in s['profiles'].items():
    print(f\"{pid}: allow={len(d.get('allowlist',[]))} deny={len(d.get('denylist',[]))}\")
print('updated:', s.get('updated'))
"
```
```
ab12cd: allow=22 deny=125
ef34gh: allow=22 deny=125
updated: 2026-10-29T14:20:31Z
```

### The union across every profile
```bash
python3 -c "
import json
s = json.load(open('sync-state.json'))
for kind in ('allowlist','denylist'):
    u = set()
    for d in s['profiles'].values():
        u |= set(d.get(kind, []))
    print(kind, len(u))
"
```

### Conflicts (a domain in both lists — should be 0)
```bash
python3 -c "
import json
s = json.load(open('sync-state.json'))
a, d = set(), set()
for p in s['profiles'].values():
    a |= set(p.get('allowlist',[])); d |= set(p.get('denylist',[]))
print('conflicts:', sorted(a & d) or 'none')
"
```

---

## 6. Resetting the state DB

```bash
# safe: start over but keep the file
echo '{"version":1,"profiles":{}}' > sync-state.json

# or delete it — the script recreates it
rm sync-state.json
```

⚠️ This forgets which domains you deleted by hand, so those may come back.

---

## 7. Git helpers

```bash
git clone https://github.com/USER/nextdns-profile-union.git
cd nextdns-profile-union

git add union.py sync-state.json .github/workflows/union-sync.yml
git commit -m "setup union sync"
git push

# when did the state DB change?
git log --oneline -- sync-state.json | head

# state DB at the last commit
git show HEAD:sync-state.json | head -20
```

---

## 8. Debugging

```bash
# keep a log
python3 union.py --dry-run 2>&1 | tee debug.log

# last 50 lines, unbuffered
python3 -u union.py --dry-run 2>&1 | tail -50

# test one profile only
export NEXTDNS_API_KEY1="..."
export NEXTDNS_PROFILE_ID1="ab12cd"
unset NEXTDNS_API_KEY2 NEXTDNS_PROFILE_ID2
python3 union.py --dry-run

# which test failed?
python3 tests/test_union.py 2>&1 | grep FAIL
```
