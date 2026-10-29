# 11 · FAQ

[⬅️ Back to index](README.md)

---

## 🚀 Getting started

**1. What is the minimum setup?**
`NEXTDNS_API_KEY1` + `NEXTDNS_PROFILE_ID1`. Everything else is optional.

**2. How many profiles are supported?**
20 by default. Raise `MAX_PROFILES = 20` in `union.py` for more.

**3. Can slot numbers have gaps (1, 2, 5)?**
Yes. The script checks 1–20 and uses whichever slots are complete.

**4. Is `NEXTDNS_LABELn` required?**
No. Without it reports show `profile 3`. Labels make the reports readable.

**5. Can several profiles share one key?**
Yes — profiles in the same NextDNS account accept the same key.

**6. Do I need the NextDNS app, RethinkDNS or a DoH proxy?**
No. This uses the NextDNS **REST API** only.

**7. Do I need Python installed?**
Not for Actions (the workflow installs it). Yes for running locally.

---

## 🔐 Security & public repos

**8. Can this repo be public?**
Yes — no credentials are committed; keys live in GitHub Variables.

**9. Then what *is* exposed?**
`sync-state.json` contains your profile ids and the exact domains you allow/block.
That is a privacy consideration, not a credential leak.

**10. Should I fork it publicly or privately?**
**Privately.** A fork carries its own `sync-state.json`, which the bot commits to on
every run. See [`13-TEMPLATE-GUIDE.md`](13-TEMPLATE-GUIDE.md).

**11. A key leaked — what now?**
NextDNS → Account → **API Key → Regenerate**, then update the variable. The old key dies.

**12. Is a leaked Telegram token dangerous?**
It allows sending messages as your bot. It grants **no** access to NextDNS.

**13. Variables vs Secrets — which is safer?**
Secrets are hidden from the UI and masked in logs. This project reads **Variables**
because the workflow passes `toJson(vars)`. It is still safe because no credentials are
committed. If you prefer Secrets, change `toJson(vars)` → `toJson(secrets)`.

**14. What can someone do with my NextDNS API key?**
Read and modify **every profile in that account**. Treat it like a password.

---

## ⚙️ Behaviour

**15. Are settings / security / blocklists synced?**
No — deliberately. Only `allowlist` and `denylist`.

**16. If I delete a domain, is it removed everywhere?**
No. This is a **union**, not a mirror. Nothing is ever deleted.

**17. What if a domain is in both the allowlist and the denylist?**
The tool never moves domains between the two lists. If you put a domain in both in
NextDNS, it stays that way.

**18. What happens to `active: false` entries?**
They are added as inactive. A domain is marked active only if it is active in at least
one profile.

**19. Why doesn't a domain I deleted by hand come back?**
Because the state DB remembers it was synced there — its absence means "the user removed
it". Use `full` if you want it back. See [`05-FULL-SYNC.md`](05-FULL-SYNC.md).

**20. When should I use `full = true`?**
Only when you want a deleted domain back, or the state DB is broken. Normally `false`.

**21. Does a new profile need special handling?**
No. A normal run fills it completely.

**22. What if a profile's list is empty?**
It counts as "read" (the `seeded` flag) and is filled on that same run.

---

## ⏱️ Timing & limits

**23. Why does a run take minutes?**
Each `POST` waits 10 seconds (rate-limit protection). 14 POSTs ≈ 140 s.
Batches of 20+ items use a single bulk `PUT` and take ~2 s.

**24. What is the schedule?**
`0 */12 * * *` — twice a day (00:00 and 12:00 UTC). Edit the cron line to change it.

**25. How many Actions minutes does it use?**
~1–5 min per run, twice a day → roughly 60–300 min/month. The free plan includes
2,000 min/month for private repos; public repos are unlimited.

**26. NextDNS rate limits?**
The tool backs off automatically on `429` (sleeps 15–80 s, then retries).

**27. Can it run more often than every 12 hours?**
Change the cron, e.g. `0 */6 * * *`. Twice a day is usually plenty because domain lists
change rarely.

---

## 🧩 Technical

**28. Is Python needed in the repo?**
Only `union.py`. No `requirements.txt` — it uses the standard library only.

**29. Can I fork and modify it?**
Yes (GPL-3.0). Do not add other endpoints to `LISTS` — see
[`08-HOW-IT-WORKS.md`](08-HOW-IT-WORKS.md) section 10.

**30. Why is `union-summary.json` not committed?**
It is per-run output and would clutter the history. Download it from the run artifacts.

**31. Where is the state DB documented?**
[`07-FILES.md`](07-FILES.md) — schema, the `seeded` flag and the rules.

**32. A test fails locally — what now?**
```bash
python3 tests/test_union.py 2>&1 | grep FAIL
```
The tests need no network or keys. The failing name points at the behaviour involved.
