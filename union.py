#!/usr/bin/env python3
"""
NextDNS Profile Union
=====================

Union sync of NextDNS `allowlist` + `denylist` across up to 20 profiles.

A domain added to ANY profile's allowlist/denylist is automatically added to
every other profile. Nothing is ever deleted and nothing is ever switched off
(add-only union). Allowlist and denylist never mix.

All configuration comes from **environment variables** (GitHub *Variables* in
Actions, plain `export` locally). No credentials are stored in this repository,
so it is safe to keep the repository public.

Variables
---------
NEXTDNS_API_KEY1 .. NEXTDNS_API_KEY20          API key of profile N
NEXTDNS_PROFILE_ID1 .. NEXTDNS_PROFILE_ID20    profile id of profile N
NEXTDNS_LABEL1 .. NEXTDNS_LABEL20              (optional) friendly name
TG_TOKEN, TG_CHAT, TG_ON                       (optional) Telegram reports
SYNC_DELAY, SYNC_BULK_THRESHOLD, SYNC_STATE_PATH,
SYNC_TIMEOUT, SYNC_RETRIES, SYNC_APPLY, ...    (optional) tuning

Usage
-----
    python3 union.py --check           # which variables are set / missing
    python3 union.py --list            # verify keys + show profile names
    python3 union.py --dry-run         # show what would be added
    python3 union.py                   # really add
    python3 union.py --full            # ignore the state DB (emergency)
    python3 union.py --no-notify       # do not send a Telegram message

See Instructions/ for the full documentation.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# =========================================================================== #
#  CONFIG  (every value can be overridden with an environment variable)
# =========================================================================== #

API = "https://api.nextdns.io"
UA = "curl/8.0 (nextdns-profile-union)"

MAX_PROFILES = 20                  # slots NEXTDNS_API_KEY1 .. 20
LISTS = ("allowlist", "denylist")  # IGNORE: the only two lists this tool touches

# Nothing secret is written in this file. Credentials are read at runtime from
# environment variables (GitHub Variables), so this repo can stay public.


def _vars() -> dict[str, str]:
    """Environment plus an optional `ALL_VARS` JSON blob (workflow uses toJson(vars))."""
    merged: dict[str, str] = {}
    raw = os.environ.get("ALL_VARS")
    if raw:
        try:
            for k, v in (json.loads(raw) or {}).items():
                if v is not None:
                    merged[str(k)] = str(v)
        except Exception:  # noqa: BLE001 - never fail because of this
            pass
    merged.update({k: v for k, v in os.environ.items() if v is not None})
    return merged


VARS = _vars()


def env(name: str, default: str = "") -> str:
    value = VARS.get(name)
    if value is None or str(value).strip() == "":
        return default
    return str(value).strip()


def env_int(name: str, default: int) -> int:
    try:
        return int(env(name, str(default)))
    except ValueError:
        return default


def env_float(name: str, default: float) -> float:
    try:
        return float(env(name, str(default)))
    except ValueError:
        return default


def env_bool(name: str, default: bool) -> bool:
    raw = env(name)
    if not raw:
        return default
    return raw.lower() in ("1", "true", "yes", "y", "on")


DELAY = env_float("SYNC_DELAY", 10.0)             # seconds between POST requests
READ_DELAY = env_float("SYNC_READ_DELAY", 0.5)    # seconds between profile reads
BACKFILL = env_bool("SYNC_BACKFILL", True)        # use bulk PUT for many items
BULK_THRESHOLD = env_int("SYNC_BULK_THRESHOLD", 20)
RETRIES = max(1, env_int("SYNC_RETRIES", 4))
TIMEOUT = max(5, env_int("SYNC_TIMEOUT", 30))
STATE_PATH = env("SYNC_STATE_PATH", "sync-state.json")
SUMMARY_PATH = env("SYNC_SUMMARY_PATH", "union-summary.json")
APPLY_DEFAULT = env_bool("SYNC_APPLY", True)

TG_TOKEN = env("TG_TOKEN")
TG_CHAT = env("TG_CHAT")
TG_ON = env_bool("TG_ON", True)


class ApiError(RuntimeError):
    pass


_DUP_HINTS = ("already", "duplicate", "conflict", "exist", "409")


def is_duplicate_error(err) -> bool:
    """True when the API refused the write because the entry already exists."""
    msg = str(err).lower()
    return any(h in msg for h in _DUP_HINTS)


# =========================================================================== #
#  PROFILES  (built from variables)
# =========================================================================== #
def load_profiles() -> tuple[list[dict], list[str]]:
    """Read NEXTDNS_API_KEYn / NEXTDNS_PROFILE_IDn / NEXTDNS_LABELn pairs.

    Returns (profiles, problems). A slot with neither value is skipped, a slot
    with only one of the two is reported as a problem but does not abort.
    """
    profiles: list[dict] = []
    problems: list[str] = []
    for i in range(1, MAX_PROFILES + 1):
        key = env(f"NEXTDNS_API_KEY{i}")
        pid = env(f"NEXTDNS_PROFILE_ID{i}")
        label = env(f"NEXTDNS_LABEL{i}") or f"profile {i}"
        if not key and not pid:
            continue
        if not key or not pid:
            missing = "NEXTDNS_API_KEY%d" % i if not key else "NEXTDNS_PROFILE_ID%d" % i
            problems.append(f"profile {i} ({label}): {missing} is empty")
            continue
        profiles.append({"slot": i, "label": label, "id": pid, "key": key})
    return profiles, problems


# =========================================================================== #
#  HTTP
# =========================================================================== #
def request(method: str, path: str, key: str, body=None, query: str = ""):
    url = f"{API}{path}{query}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"X-Api-Key": key, "Accept": "application/json", "User-Agent": UA}
    if data:
        headers["Content-Type"] = "application/json"

    last = None
    for attempt in range(1, RETRIES + 1):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                raw = resp.read().decode() or "{}"
                payload = json.loads(raw) if raw.strip() else {}
                if payload.get("errors"):
                    raise ApiError(f"{method} {path} -> {payload['errors']}")
                return payload
        except urllib.error.HTTPError as e:
            raw = e.read().decode(errors="replace")
            if e.code not in (429, 500, 502, 503, 504):
                raise ApiError(f"{method} {path} -> HTTP {e.code}: {raw[:200]}") from None
            last = f"HTTP {e.code}"
            if e.code == 429:
                wait = max(15, 20 * attempt)
                print(f"    ! 429 rate limit - waiting {wait}s")
                time.sleep(wait)
                continue
        except (urllib.error.URLError, TimeoutError) as e:
            last = f"{type(e).__name__}: {e}"
        if attempt < RETRIES:
            time.sleep(2 * attempt)
    raise ApiError(f"{method} {path} failed after {RETRIES} attempts: {last}")


def get_list(profile_id: str, key: str, kind: str) -> list[dict]:
    """Read a whole list, following pagination cursors."""
    out, cursor = [], None
    for _ in range(200):
        q = f"?cursor={cursor}" if cursor else ""
        payload = request("GET", f"/profiles/{profile_id}/{kind}", key, query=q)
        page = payload.get("data") or []
        out.extend(page)
        cursor = (payload.get("meta") or {}).get("pagination", {}).get("cursor")
        if not cursor or not page:
            break
    return out


def normalise(entries: list[dict]) -> dict[str, bool]:
    """[{id, active}, ...] -> {domain: active}, lowercased and de-duplicated."""
    out: dict[str, bool] = {}
    for e in entries or []:
        d = (e.get("id") or "").strip().lower()
        if not d:
            continue
        out[d] = bool(e.get("active", True)) or out.get(d, False)
    return out


# =========================================================================== #
#  TELEGRAM  (never fatal)
# =========================================================================== #
def tg_esc(text) -> str:
    """Escape the three characters HTML parse mode cares about."""
    return (str(text).replace("&", "&amp;")
            .replace("<", "&lt;").replace(">", "&gt;"))


def tg_on() -> bool:
    return bool(TG_ON and TG_TOKEN and TG_CHAT)


def notify(text: str, tries: int = 3) -> bool:
    """Send a Telegram message. Never raises, never blocks the sync."""
    if not tg_on():
        print("  (telegram off - no message sent)")
        return False
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    body = {"chat_id": TG_CHAT, "text": text[:4000],
            "disable_web_page_preview": True, "parse_mode": "HTML"}
    for attempt in range(1, tries + 1):
        payload = json.dumps(body).encode()
        try:
            req = urllib.request.Request(
                url, data=payload, method="POST",
                headers={"Content-Type": "application/json", "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                ok = json.loads(r.read().decode() or "{}").get("ok")
            if ok:
                print("  telegram message sent")
                return True
            print(f"  ! telegram: ok=false ({attempt}/{tries})")
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:200]
            print(f"  ! telegram failed ({attempt}/{tries}): HTTP {e.code} {detail}")
            if e.code == 400 and body.get("parse_mode"):
                # HTML could not be parsed - retry as plain text
                body.pop("parse_mode", None)
                for tag in ("<b>", "</b>", "<i>", "</i>", "<code>", "</code>",
                            "<pre>", "</pre>"):
                    text = text.replace(tag, "")
                body["text"] = text[:4000]
                continue
        except Exception as e:  # noqa: BLE001
            print(f"  ! telegram failed ({attempt}/{tries}): {e}")
        time.sleep(2 * attempt)
    print("  ! telegram: message not delivered (sync itself is unaffected)")
    return False


def build_report(results: list, apply: bool, full: bool, errors: list,
                 started: float, count: int) -> str:
    """Build the HTML summary that is sent to Telegram after every run."""
    if not apply:
        head = "NextDNS profile union - DRY-RUN"
        icon = "🔍"
    elif full:
        head = "NextDNS profile union - FULL"
        icon = "✅" if not errors else "⚠️"
    else:
        head = "NextDNS profile union"
        icon = "✅" if not errors else "⚠️"

    lines = [
        f"{icon} <b>{tg_esc(head)}</b>",
        f"<code>{count} profiles - {time.time() - started:.0f}s</code>",
        f"<code>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</code>",
        "",
    ]
    for r in results:
        total = sum(r["added"].values()) if r["added"] else 0
        tag = []
        if r.get("seeded"):
            tag.append("seed")
        if r.get("written"):
            tag.append(f"{r['written']} write")
        if r.get("skipped"):
            tag.append(f"{r['skipped']} skip")
        if r.get("errors"):
            tag.append(f"{len(r['errors'])} error")
        suffix = ("  <i>" + tg_esc(" - ".join(tag)) + "</i>") if tag else ""
        lines.append(f"• <b>{tg_esc(r['kind'])}</b> - union <code>{r['union']}</code>"
                     f" - added <code>{total}</code>{suffix}")

    if not apply:
        lines += ["", "<i>dry-run - nothing was written</i>"]
    elif not errors:
        lines += ["", "<b>Everything is in sync</b> ✅"]
    else:
        lines += ["", f"<b>{len(errors)} error(s)</b> - will be retried on the next run"]
        for e in errors[:8]:
            lines.append(f"  <code>{tg_esc(e[:160])}</code>")
        if len(errors) > 8:
            lines.append(f"  <i>... and {len(errors) - 8} more</i>")
    return "\n".join(lines)


# =========================================================================== #
#  STATE DB  (sync-state.json, committed by the workflow)
# =========================================================================== #
def load_state() -> dict:
    path = Path(STATE_PATH)
    if not path.exists():
        return {"version": 1, "profiles": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "profiles" not in data:
            raise ValueError("unexpected structure")
        return data
    except Exception as e:  # noqa: BLE001
        print(f"  ! cannot read the state file ({e}) - starting from an empty state")
        return {"version": 1, "profiles": {}}


def save_state(state: dict) -> None:
    state["version"] = 1
    state["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # sorted output keeps the git diff clean and stable
    state["profiles"] = {
        pid: {k: sorted(set(v)) for k, v in sorted(lists.items()) if v}
        for pid, lists in sorted(state["profiles"].items())
    }
    try:
        Path(STATE_PATH).write_text(
            json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        print(f"  ! could not save the state file ({e})")


def seen_domains(state: dict, profile_id: str, kind: str) -> set[str]:
    return set((state["profiles"].get(profile_id) or {}).get(kind) or [])


def is_seeded(state: dict, profile_id: str, kind: str) -> bool:
    """Has this profile + list already been read at least once?

    An EMPTY list still counts as seeded. Without this flag an empty profile
    would look like "first run" on every single run and would never be filled.
    """
    entry = state["profiles"].get(profile_id) or {}
    return kind in (entry.get("seeded") or [])


def mark_seeded(state: dict, profile_id: str, kind: str) -> None:
    entry = state["profiles"].setdefault(profile_id, {})
    seeded = set(entry.get("seeded") or [])
    seeded.add(kind)
    entry["seeded"] = sorted(seeded)


def remember(state: dict, profile_id: str, kind: str, domains) -> None:
    entry = state["profiles"].setdefault(profile_id, {})
    current = set(entry.get(kind) or [])
    current |= {d.lower() for d in domains}
    entry[kind] = sorted(current)


# =========================================================================== #
#  SYNC
# =========================================================================== #
def list_profiles(profiles: list[dict]) -> None:
    for p in profiles:
        try:
            data = request("GET", f"/profiles/{p['id']}", p["key"]).get("data") or {}
            print(f"  [{p['slot']:>2}] {p['label']:<16} {p['id']:<10} -> {data.get('name')!r}")
        except Exception as e:  # noqa: BLE001
            print(f"  [{p['slot']:>2}] {p['label']:<16} {p['id']:<10} -> ERROR {e}")


def check_config(profiles: list[dict], problems: list[str]) -> None:
    print(f"profiles found: {len(profiles)} / {MAX_PROFILES}")
    for p in profiles:
        key_tail = p["key"][-4:] if len(p["key"]) > 4 else "????"
        state = "suspicious" if len(p["key"]) < 20 else "ok"
        print(f"  [{p['slot']:>2}] {p['label']:<16} id={p['id']:<10} "
              f"key=...{key_tail} ({state})")
    if problems:
        print("\n  variables that need attention:")
        for pr in problems:
            print(f"  ! {pr}")
    if not profiles:
        print("\n!! No profile was found.")
        print("!! Go to Settings > Secrets and variables > Actions > Variables and add")
        print("!! NEXTDNS_API_KEY1 together with NEXTDNS_PROFILE_ID1.")
    print(f"\ntelegram: {'on' if tg_on() else 'off'} - delay={DELAY:g}s - "
          f"bulk>={BULK_THRESHOLD} - state={STATE_PATH}")


def sync_kind(kind: str, apply: bool, state: dict, profiles: list[dict],
              full: bool = False) -> dict:
    """Union sync one list (allowlist or denylist) across every profile."""
    print(f"\n=== {kind} ===")
    per_profile: dict[str, dict[str, bool]] = {}
    errors: list[str] = []
    for p in profiles:
        try:
            per_profile[p["id"]] = normalise(get_list(p["id"], p["key"], kind))
            print(f"  read {p['label']:<16} {len(per_profile[p['id']])} entries")
        except Exception as e:  # noqa: BLE001 - one broken profile must not stop the rest
            print(f"  read {p['label']:<16} ERROR {e}  -> skipping this profile")
            errors.append(f"read {p['label']} {kind}: {e}")
        time.sleep(READ_DELAY)

    union: dict[str, bool] = {}
    for entries in per_profile.values():
        for domain, active in entries.items():
            # a domain is active if it is active in ANY profile
            union[domain] = union.get(domain, False) or active
    print(f"  union: {len(union)} unique domains")

    added: dict[str, int] = {}
    skipped_total = 0
    seeded_any = False
    writes = 0
    bulk_written = 0

    for p in profiles:
        if p["id"] not in per_profile:      # read failed -> leave it for the next run
            continue
        have = per_profile[p["id"]]
        already = seen_domains(state, p["id"], kind)

        # First time we see this profile + list: put what it already has into the
        # state DB and keep going in the SAME run. Domains it already has are not
        # written again, so nothing is duplicated.
        if not is_seeded(state, p["id"], kind):
            remember(state, p["id"], kind, have.keys())
            mark_seeded(state, p["id"], kind)
            seeded_any = True
            print(f"  {p['label']:<16} first run - seeded the state DB, syncing now")
            already = seen_domains(state, p["id"], kind)

        todo, skipped = [], 0
        for domain in sorted(union):
            if domain in have:
                continue
            if not full and domain in already:
                # synced before but missing now -> the user deleted it on purpose
                skipped += 1
                continue
            todo.append((domain, union[domain]))

        added[p["label"]] = len(todo)
        skipped_total += skipped

        if not todo:
            note = f" ({skipped} skipped - already synced before)" if skipped else ""
            print(f"  {p['label']:<16} up to date{note}")
            if apply:
                remember(state, p["id"], kind, have.keys())
            continue

        if not apply:
            if BACKFILL and len(todo) >= BULK_THRESHOLD:
                print(f"  {p['label']:<16} BULK PUT would write {len(todo)} new entries")
            else:
                print(f"  {p['label']:<16} +{len(todo)} to add: "
                      + ", ".join(d for d, _ in todo[:8])
                      + (" ..." if len(todo) > 8 else ""))
            continue

        # ---- bulk backfill: many items at once (1 PUT instead of N POSTs) ----
        if BACKFILL and len(todo) >= BULK_THRESHOLD:
            try:
                entries = [dict(e) for e in get_list(p["id"], p["key"], kind)]
                existing = {(e.get("id") or "").lower() for e in entries}
                for domain, active in todo:
                    if domain not in existing:
                        entries.append({"id": domain, "active": active})
                        existing.add(domain)
                request("PUT", f"/profiles/{p['id']}/{kind}", p["key"], body=entries)
                after = {(e.get("id") or "").lower()
                         for e in get_list(p["id"], p["key"], kind)}
                ok = {d for d, _ in todo} <= after
                remember(state, p["id"], kind, after | have.keys())
                if ok:
                    bulk_written += len(todo)
                    print(f"  {p['label']:<16} BULK PUT {len(entries)} entries (verified)")
                    continue
                print(f"  {p['label']:<16} BULK PUT {len(entries)} entries "
                      f"(verification FAILED -> falling back to POST)")
                errors.append(f"{p['label']} {kind}: bulk PUT verification failed")
            except Exception as e:  # noqa: BLE001 - fall back to POST one by one
                print(f"  {p['label']:<16} bulk PUT failed ({e}) -> falling back to POST")
                errors.append(f"{p['label']} {kind} bulk: {e}")

        print(f"  {p['label']:<16} +{len(todo)} to add: "
              + ", ".join(d for d, _ in todo[:8]) + (" ..." if len(todo) > 8 else ""))

        failed = 0
        for domain, active in todo:
            try:
                request("POST", f"/profiles/{p['id']}/{kind}", p["key"],
                        body={"id": domain, "active": active})
                writes += 1
                remember(state, p["id"], kind, [domain])
                print(f"      + {domain}  ({writes} written, {DELAY:g}s cooldown)")
            except Exception as e:  # noqa: BLE001 - skip it and continue
                failed += 1
                errors.append(f"{p['label']} {kind} {domain}: {e}")
                print(f"      ! {domain} skipped ({e})")
                if is_duplicate_error(e):
                    # it already exists -> remember it so we never try again
                    remember(state, p["id"], kind, [domain])
            time.sleep(DELAY)      # abuse / rate-limit protection
        if failed:
            print(f"      {failed} item(s) skipped - the rest went through")

        remember(state, p["id"], kind, have.keys())

    if apply:
        for p in profiles:
            if p["id"] in per_profile:
                remember(state, p["id"], kind, per_profile[p["id"]].keys())
        save_state(state)

    return {"kind": kind, "union": len(union), "added": added,
            "skipped": skipped_total, "seeded": seeded_any,
            "errors": errors, "written": writes + bulk_written}


# =========================================================================== #
#  MAIN
# =========================================================================== #
def main() -> int:
    args = sys.argv[1:]
    started = time.time()
    profiles, problems = load_profiles()

    if "--check" in args:
        check_config(profiles, problems)
        return 0 if profiles else 2

    if "--list" in args:
        print("profiles:")
        list_profiles(profiles)
        return 0

    if not profiles:
        msg = ("No profile was found. Add the NEXTDNS_API_KEY1 and "
               "NEXTDNS_PROFILE_ID1 variables first.")
        print(f"\n!! {msg}")
        for pr in problems:
            print(f"!! {pr}")
        if "--no-notify" not in args:
            notify("🛑 <b>NextDNS profile union - run aborted</b>\n\n"
                   f"<code>{tg_esc(msg)}</code>")
        return 2

    apply = APPLY_DEFAULT and "--dry-run" not in args
    full = "--full" in args

    print(f"nextdns profile union - {len(profiles)}/{MAX_PROFILES} profiles - "
          f"lists={','.join(LISTS)} - {'APPLY' if apply else 'DRY-RUN'}"
          f"{' - FULL' if full else ''} - delay={DELAY:g}s - state={STATE_PATH}")
    if problems:
        print("variables that need attention:")
        for pr in problems:
            print(f"  ! {pr}")

    state = load_state()
    known = sum(len(v.get("denylist") or []) + len(v.get("allowlist") or [])
                for v in state["profiles"].values())
    print(f"state: {len(state['profiles'])} profiles - {known} known entries")

    results = [sync_kind(kind, apply, state, profiles, full=full) for kind in LISTS]

    print("\n=== summary ===")
    all_errors = [e for r in results for e in (r.get("errors") or [])]
    for r in results:
        total = sum(r["added"].values()) if r["added"] else 0
        extra = " - SEEDED" if r.get("seeded") else (
            f" - skipped {r['skipped']}" if r.get("skipped") else "")
        if r.get("errors"):
            extra += f" - {len(r['errors'])} error(s)"
        print(f"  {r['kind']:<10} union={r['union']:<5} added={total}{extra}")

    if all_errors:
        print("\n=== errors (skipped, will be retried on the next run) ===")
        for e in all_errors:
            print(f"  ! {e}")
    print("\nDONE" if apply else "\nDRY-RUN finished (nothing written)")

    try:
        Path(SUMMARY_PATH).write_text(json.dumps(
            {"results": results, "problems": problems}, indent=2), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

    if "--no-notify" not in args:
        notify(build_report(results, apply, full, all_errors, started, len(profiles)))
    return 0


def run_guarded() -> int:
    """Even a crash is reported, so a silent failure is impossible."""
    try:
        return main()
    except KeyboardInterrupt:
        return 130
    except SystemExit:
        raise
    except BaseException as e:  # noqa: BLE001
        import traceback
        tb = traceback.format_exc()
        print(f"\nERROR: {e}", file=sys.stderr)
        if "--no-notify" not in sys.argv[1:]:
            notify("💥 <b>NextDNS profile union - CRASH</b>\n\n"
                   f"<code>{tg_esc(type(e).__name__)}: {tg_esc(str(e)[:300])}</code>\n\n"
                   "<pre>" + tg_esc("\n".join(tb.strip().splitlines()[-8:])) + "</pre>")
        return 1


if __name__ == "__main__":
    sys.exit(run_guarded())
