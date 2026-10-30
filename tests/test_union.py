#!/usr/bin/env python3
"""Offline tests for union.py — fake NextDNS API, no network, no Telegram."""

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("TG_ON", "false")
import union as u  # noqa: E402

REAL_NOTIFY = u.notify

# --------------------------------------------------------------------------- #
# fake NextDNS API
# --------------------------------------------------------------------------- #
DB: dict = {}
WRITES: list = []
FAIL_READS: set = set()
FAIL_POSTS: set = set()
FAIL_POSTS_500: set = set()


class FakeApiError(Exception):
    pass


def fake_request(method, path, key, body=None, query=""):
    parts = [p for p in path.split("/") if p]
    if parts == ["profiles"]:
        return {"data": [{"id": k, "name": k} for k in DB]}
    pid = parts[1]
    if pid in FAIL_READS:
        raise FakeApiError(f"GET /profiles/{pid} -> HTTP 500: boom")
    if len(parts) == 2:
        return {"data": {"id": pid, "name": pid}}
    kind = parts[2]
    if method == "GET":
        return {"data": DB[pid][kind], "meta": {"pagination": {"cursor": None}}}
    if method == "PUT":
        WRITES.append((method, pid, kind, {"bulk": len(body)}))
        DB[pid][kind] = [dict(e) for e in body]
        return {"data": None}
    if method == "POST":
        if body.get("id") in FAIL_POSTS_500:
            raise FakeApiError(f"POST /profiles/{pid}/{kind} -> HTTP 500: boom")
        if body.get("id") in FAIL_POSTS:
            raise FakeApiError('POST -> HTTP 400: {"errors":[{"code":"duplicate",'
                               '"detail":"domain already exists"}]}')
        WRITES.append((method, pid, kind, dict(body)))
        DB[pid][kind].append({"id": body["id"], "active": body.get("active", True)})
        return {"data": None}
    raise AssertionError(f"unexpected {method} {path}")


def make_profiles(n=3):
    return [{"slot": i, "label": f"p{i}", "id": f"p{i}", "key": f"k{i}"}
            for i in range(1, n + 1)]


def setup(tmpdir, n=3):
    global DB, WRITES, FAIL_READS, FAIL_POSTS, FAIL_POSTS_500
    DB = {
        "p1": {"allowlist": [{"id": "a.com", "active": True},
                             {"id": "x.com", "active": True}],
               "denylist": [{"id": "ads.com", "active": True}]},
        "p2": {"allowlist": [{"id": "b.com", "active": True}], "denylist": []},
        "p3": {"allowlist": [], "denylist": [{"id": "track.com", "active": False}]},
    }
    WRITES = []
    FAIL_READS = set()
    FAIL_POSTS = set()
    FAIL_POSTS_500 = set()
    u.request = fake_request
    u.notify = REAL_NOTIFY
    u.TG_ON = False
    u.DELAY = 0
    u.READ_DELAY = 0
    u.BACKFILL = True
    u.BULK_THRESHOLD = 3
    u.RETRIES = 1
    u.STATE_PATH = os.path.join(tmpdir, "sync-state.json")
    u.SUMMARY_PATH = os.path.join(tmpdir, "union-summary.json")
    # main() reads the config from variables -> point them at the fake profiles
    env = {}
    for i in range(1, n + 1):
        env[f"NEXTDNS_API_KEY{i}"] = f"k{i}"
        env[f"NEXTDNS_PROFILE_ID{i}"] = f"p{i}"
    u.VARS = env
    return make_profiles(n)


def run_all(profiles, apply=True, full=False):
    state = u.load_state()
    return [u.sync_kind(k, apply, state, profiles, full=full) for k in u.LISTS]


def state_json():
    return json.loads(Path(u.STATE_PATH).read_text())


# --------------------------------------------------------------------------- #
# variables / profiles
# --------------------------------------------------------------------------- #
def test_profiles_are_read_from_numbered_variables():
    env = {"NEXTDNS_API_KEY1": "k1", "NEXTDNS_PROFILE_ID1": "id1",
           "NEXTDNS_API_KEY2": "k2", "NEXTDNS_PROFILE_ID2": "id2",
           "NEXTDNS_LABEL2": "Amma",
           "NEXTDNS_API_KEY3": "k3", "NEXTDNS_PROFILE_ID3": "id3"}
    old = u.VARS
    try:
        u.VARS = dict(env)
        profiles, problems = u.load_profiles()
    finally:
        u.VARS = old
    assert [p["id"] for p in profiles] == ["id1", "id2", "id3"], profiles
    assert profiles[1]["label"] == "Amma", profiles
    assert profiles[0]["label"] == "profile 1", profiles
    assert problems == [], problems


def test_half_configured_profile_is_reported_not_crashing():
    old = u.VARS
    try:
        u.VARS = {"NEXTDNS_API_KEY1": "k1",          # id missing
                  "NEXTDNS_PROFILE_ID2": "id2"}      # key missing
        profiles, problems = u.load_profiles()
    finally:
        u.VARS = old
    assert profiles == [], profiles
    assert len(problems) == 2, problems
    assert "NEXTDNS_PROFILE_ID1" in problems[0], problems
    assert "NEXTDNS_API_KEY2" in problems[1], problems


def test_twenty_slots_are_supported():
    old = u.VARS
    try:
        env = {}
        for i in range(1, 21):
            env[f"NEXTDNS_API_KEY{i}"] = f"k{i}"
            env[f"NEXTDNS_PROFILE_ID{i}"] = f"id{i}"
        u.VARS = dict(env)
        profiles, problems = u.load_profiles()
    finally:
        u.VARS = old
    assert len(profiles) == 20, len(profiles)
    assert [p["slot"] for p in profiles] == list(range(1, 21)), profiles
    assert problems == []


def test_gaps_in_numbering_are_fine():
    old = u.VARS
    try:
        u.VARS = {"NEXTDNS_API_KEY1": "k1", "NEXTDNS_PROFILE_ID1": "id1",
                  "NEXTDNS_API_KEY7": "k7", "NEXTDNS_PROFILE_ID7": "id7"}
        profiles, problems = u.load_profiles()
    finally:
        u.VARS = old
    assert [p["slot"] for p in profiles] == [1, 7], profiles


def test_no_profiles_exits_with_code_2():
    old_v, old_argv = u.VARS, sys.argv
    sent = []
    u.notify = lambda text, tries=3: sent.append(text) or True
    try:
        u.VARS = {}
        sys.argv = ["union.py", "--dry-run"]
        assert u.main() == 2
    finally:
        u.VARS, sys.argv, u.notify = old_v, old_argv, REAL_NOTIFY
    assert sent and "No profile was found" in sent[0], sent


def test_labels_are_optional_and_fall_back_to_profile_number():
    old = u.VARS
    try:
        u.VARS = {"NEXTDNS_API_KEY5": "k5", "NEXTDNS_PROFILE_ID5": "id5"}
        profiles, _ = u.load_profiles()
    finally:
        u.VARS = old
    assert profiles[0]["label"] == "profile 5", profiles


# --------------------------------------------------------------------------- #
# first run / seeding
# --------------------------------------------------------------------------- #
def test_first_run_seeds_db_and_fills_everyone_in_one_go():
    with tempfile.TemporaryDirectory() as d:
        profiles = setup(d)
        res = run_all(profiles)
        assert all(r["seeded"] for r in res), res
        st = state_json()["profiles"]
        assert set(st) == {"p1", "p2", "p3"}, st
        assert st["p2"]["allowlist"] == ["a.com", "b.com", "x.com"], st["p2"]
        assert st["p3"]["denylist"] == ["ads.com", "track.com"], st["p3"]
        assert st["p1"]["seeded"] == ["allowlist", "denylist"], st["p1"]
        n = len(WRITES)
        run_all(profiles)          # 2nd run must not duplicate anything
        assert len(WRITES) == n, f"duplicates on 2nd run: {WRITES[n:]}"


def test_empty_profile_is_filled_on_the_very_first_run():
    with tempfile.TemporaryDirectory() as d:
        profiles = setup(d)
        run_all(profiles)
        for pid in DB:
            assert "a.com" in {e["id"] for e in DB[pid]["allowlist"]}, pid


# --------------------------------------------------------------------------- #
# propagation / duplicates
# --------------------------------------------------------------------------- #
def test_new_domain_propagates_to_everyone():
    with tempfile.TemporaryDirectory() as d:
        profiles = setup(d)
        run_all(profiles)                                   # seed
        DB["p1"]["denylist"].append({"id": "newblock.com", "active": True})
        run_all(profiles)
        for pid in DB:
            assert "newblock.com" in {e["id"] for e in DB[pid]["denylist"]}, pid


def test_domain_added_twice_is_not_re_added():
    with tempfile.TemporaryDirectory() as d:
        profiles = setup(d)
        run_all(profiles)
        DB["p1"]["denylist"].append({"id": "once.com", "active": True})
        run_all(profiles)
        n = len(WRITES)
        run_all(profiles)
        assert len(WRITES) == n, f"duplicate writes: {WRITES[n:]}"
        for pid in DB:
            ids = [e["id"] for e in DB[pid]["denylist"]]
            assert ids.count("once.com") <= 1, (pid, ids)


def test_manual_delete_is_not_resurrected():
    with tempfile.TemporaryDirectory() as d:
        profiles = setup(d)
        run_all(profiles)
        run_all(profiles)
        assert "ads.com" in {e["id"] for e in DB["p2"]["denylist"]}
        DB["p2"]["denylist"] = [e for e in DB["p2"]["denylist"] if e["id"] != "ads.com"]
        before = len(WRITES)
        res = run_all(profiles)
        assert len(WRITES) == before, f"resurrected: {WRITES[before:]}"
        assert res[1]["skipped"] >= 1, res[1]


def test_full_flag_restores_everything():
    with tempfile.TemporaryDirectory() as d:
        profiles = setup(d)
        run_all(profiles)
        run_all(profiles)
        DB["p2"]["denylist"] = [e for e in DB["p2"]["denylist"] if e["id"] != "ads.com"]
        run_all(profiles, full=True)
        assert "ads.com" in {e["id"] for e in DB["p2"]["denylist"]}, "full must re-add"


# --------------------------------------------------------------------------- #
# allowlist / denylist separation
# --------------------------------------------------------------------------- #
def test_allow_and_deny_never_mix():
    with tempfile.TemporaryDirectory() as d:
        profiles = setup(d)
        run_all(profiles)
        DB["p1"]["allowlist"].append({"id": "allow-only.com", "active": True})
        DB["p1"]["denylist"].append({"id": "deny-only.com", "active": True})
        run_all(profiles)
        for pid in DB:
            allow = {e["id"] for e in DB[pid]["allowlist"]}
            deny = {e["id"] for e in DB[pid]["denylist"]}
            assert "allow-only.com" in allow and "allow-only.com" not in deny, pid
            assert "deny-only.com" in deny and "deny-only.com" not in allow, pid


def test_only_two_lists_are_configured():
    assert u.LISTS == ("allowlist", "denylist"), u.LISTS


# --------------------------------------------------------------------------- #
# bulk backfill
# --------------------------------------------------------------------------- #
def test_backfill_uses_one_bulk_put_for_empty_profile():
    with tempfile.TemporaryDirectory() as d:
        profiles = setup(d)
        run_all(profiles)
        for n in range(5):
            DB["p1"]["denylist"].append({"id": f"bulk{n}.com", "active": True})
        WRITES.clear()
        run_all(profiles)
        puts = [w for w in WRITES if w[0] == "PUT"]
        p3_posts = [w for w in WRITES if w[0] == "POST" and w[1] == "p3"]
        assert puts, WRITES
        assert not p3_posts, f"empty profile got {len(p3_posts)} POSTs instead of a PUT"
        assert {e["id"] for e in DB["p3"]["denylist"]} >= {f"bulk{n}.com" for n in range(5)}


def test_backfill_keeps_existing_entries_and_flags():
    with tempfile.TemporaryDirectory() as d:
        profiles = setup(d)
        run_all(profiles)
        DB["p1"]["denylist"].append({"id": "new1.com", "active": False})
        run_all(profiles)
        ids = [e["id"] for e in DB["p3"]["denylist"]]
        assert ids.count("track.com") == 1, ids


# --------------------------------------------------------------------------- #
# errors are skipped, never fatal
# --------------------------------------------------------------------------- #
def test_duplicate_error_is_skipped_and_does_not_kill_the_run():
    with tempfile.TemporaryDirectory() as d:
        profiles = setup(d)
        run_all(profiles)
        u.BULK_THRESHOLD = 99
        FAIL_POSTS.update({"dup1.com", "dup2.com"})
        DB["p1"]["denylist"] += [{"id": "dup1.com", "active": True},
                                 {"id": "dup2.com", "active": True},
                                 {"id": "good.com", "active": True}]
        res = run_all(profiles)
        for pid in DB:
            assert "good.com" in {e["id"] for e in DB[pid]["denylist"]}, pid
        errs = [e for r in res for e in r["errors"]]
        assert any("dup1.com" in e for e in errs), errs
        assert "dup1.com" in state_json()["profiles"]["p2"]["denylist"]
        n = len(WRITES)
        run_all(profiles)
        retried = [w for w in WRITES[n:] if w[3].get("id") in {"dup1.com", "dup2.com"}]
        assert not retried, f"duplicate retried: {retried}"


def test_http_error_is_skipped_but_retried_next_run():
    with tempfile.TemporaryDirectory() as d:
        profiles = setup(d)
        run_all(profiles)
        u.BULK_THRESHOLD = 99
        FAIL_POSTS_500.add("only-this.com")
        DB["p1"]["denylist"] += [{"id": "only-this.com", "active": True},
                                 {"id": "and-this.com", "active": True}]
        res = run_all(profiles)
        for pid in DB:
            assert "and-this.com" in {e["id"] for e in DB[pid]["denylist"]}, pid
        assert any("only-this.com" in e for r in res for e in r["errors"]), res
        assert "only-this.com" not in state_json()["profiles"]["p3"]["denylist"]
        FAIL_POSTS_500.clear()
        run_all(profiles)
        for pid in DB:
            assert "only-this.com" in {e["id"] for e in DB[pid]["denylist"]}, pid


def test_failed_profile_read_does_not_stop_the_others():
    with tempfile.TemporaryDirectory() as d:
        profiles = setup(d)
        run_all(profiles)
        FAIL_READS.add("p2")
        DB["p1"]["denylist"].append({"id": "still-works.com", "active": True})
        run_all(profiles)
        assert "still-works.com" in {e["id"] for e in DB["p3"]["denylist"]}
        assert "still-works.com" not in {e["id"] for e in DB["p2"]["denylist"]}


# --------------------------------------------------------------------------- #
# safety / state
# --------------------------------------------------------------------------- #
def test_dry_run_writes_nothing():
    with tempfile.TemporaryDirectory() as d:
        profiles = setup(d)
        run_all(profiles, apply=False)
        assert WRITES == [], WRITES


def test_nothing_deleted_and_no_settings_touched():
    with tempfile.TemporaryDirectory() as d:
        profiles = setup(d)
        paths = []

        def spy(method, path, key, body=None, query=""):
            paths.append((method, path))
            return fake_request(method, path, key, body, query)

        u.request = spy
        run_all(profiles)
        run_all(profiles)
        bad = [p for p in paths if any(x in p[1] for x in
               ("/security", "/settings", "/privacy", "/parentalControl", "/blocklists"))]
        assert not bad, bad
        assert all(p[1].split("/")[-1] in ("allowlist", "denylist") for p in paths), paths
        assert not any(p[0] == "DELETE" for p in paths), paths


def test_state_file_survives_reload():
    with tempfile.TemporaryDirectory() as d:
        profiles = setup(d)
        run_all(profiles)
        run_all(profiles)
        first = Path(u.STATE_PATH).read_text()
        run_all(profiles)
        second = Path(u.STATE_PATH).read_text()
        assert json.loads(first)["profiles"] == json.loads(second)["profiles"]


def test_uppercase_and_duplicates_collapse():
    assert u.normalise([{"id": "A.com", "active": True},
                        {"id": "a.com", "active": True}]) == {"a.com": True}


# --------------------------------------------------------------------------- #
# telegram
# --------------------------------------------------------------------------- #
def test_telegram_summary_is_sent_after_every_run():
    with tempfile.TemporaryDirectory() as d:
        profiles = setup(d)
        sent = []
        u.notify = lambda text, tries=3: sent.append(text) or True
        old = sys.argv
        try:
            sys.argv = ["union.py", "--dry-run"]
            assert u.main() == 0
        finally:
            sys.argv = old
            u.notify = REAL_NOTIFY
        assert len(sent) == 1, sent
        assert "DRY-RUN" in sent[0], sent[0]


def test_no_notify_flag_sends_nothing():
    with tempfile.TemporaryDirectory() as d:
        setup(d)
        sent = []
        u.notify = lambda text, tries=3: sent.append(text) or True
        old = sys.argv
        try:
            sys.argv = ["union.py", "--dry-run", "--no-notify"]
            u.main()
        finally:
            sys.argv = old
            u.notify = REAL_NOTIFY
        assert sent == [], sent


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except Exception as e:  # noqa: BLE001
                failures += 1
                print(f"FAIL {name}: {e!r}")
    print(f"\n{'ALL TESTS PASS ✅' if not failures else f'{failures} FAILED ❌'}")
    sys.exit(1 if failures else 0)
  
