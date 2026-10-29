# 06 · Telegram reports

[⬅️ Back to index](README.md)

---

## Why

Every run sends one message: what was added, what failed, and whether the run crashed.
You never have to open GitHub to know that sync is healthy.

---

## Step 1 — Create a bot

```
1. Telegram → @BotFather → /newbot
2. Name:  NextDNS profile union        (anything)
3. Username: nextdns_union_xxx_bot     (must be unique and end in "bot")
4. BotFather replies with:

   1234567890:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   this is TG_TOKEN
```

---

## Step 2 — Get your chat id

### Option A — `getUpdates` (most reliable)
```
1. Send /start to your new bot
2. Open this URL in a browser (replace <TOKEN> including the "bot" prefix):

   https://api.telegram.org/bot<TOKEN>/getUpdates

3. Find:

   "message":{"message_id":1,"from":{"id":123456789, ...

                                       ^^^^^^^^^
                                       this is TG_CHAT
```

### Option B — `@userinfobot`
Send `/start` to `@userinfobot`; it replies with your numeric id.

> ⚠️ **Groups** use negative ids like `-100…`. Add the bot to the group, send a message
> there, then read `getUpdates`.

---

## Step 3 — Add the variables

```
Repo → Settings → Secrets and variables → Actions → Variables → New repository variable
```

| Name | Value |
|---|---|
| `TG_TOKEN` | `1234567890:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `TG_CHAT` | `123456789` |
| `TG_ON` | `true` |

> Use the **Variables** tab (that is what the workflow reads).

---

## Step 4 — Test it

```
Actions → NextDNS profile union → Run workflow
   dry_run = true
   full    = false
```

Within ~10 seconds you should receive:

```
🔍 NextDNS profile union - DRY-RUN
3 profiles - 8s
2026-10-29 14:20 UTC

• allowlist - union 22 - added 0
• denylist - union 125 - added 0

dry-run - nothing was written
```

No message? → [`09-TROUBLESHOOTING.md`](09-TROUBLESHOOTING.md) section C.

---

## 📩 Message types

| Event | Message |
|---|---|
| run succeeded | `✅` + profile count + allowlist/denylist numbers |
| some items were skipped | `⚠️` + `N error(s)` + the first 8 errors |
| the script crashed | `💥 … CRASH` + exception + traceback |
| the job failed or was cancelled | `💥 … job failed/cancelled` + a link to the run |
| variables are missing | `🛑 … run aborted` + what is missing |
| dry-run | `🔍 … DRY-RUN` + "nothing was written" |
| full run | `✅ … - FULL` |

### Example with errors

```
⚠️ NextDNS profile union
3 profiles - 42s
2026-10-29 14:20 UTC

• allowlist - union 22 - added 0
• denylist - union 125 - added 3  3 write - 1 skip - 1 error

1 error(s) - will be retried on the next run
  Phone denylist boom.com: POST /profiles/ef34gh/denylist -> HTTP 500
```

---

## ⚙️ Turning it off

| Scope | How |
|---|---|
| Permanently | set `TG_ON = false` |
| Permanently (alternative) | delete `TG_TOKEN` or `TG_CHAT` |
| One local run | `python3 union.py --no-notify` |

---

## 🛡️ Telegram failures never break the sync

```
telegram message sent                          ← delivered
! telegram failed (1/3): HTTP 401             ← retrying
! telegram: message not delivered (sync itself is unaffected)
```

Three attempts, then it gives up silently. The sync continues normally.

---

## 🔐 Is the token safe?

| Item | Status |
|---|---|
| In the repository | ❌ no — it lives in Variables |
| Safe in a public repo | ✅ yes |
| Leaked? | BotFather → `/revoke` → update the variable |
| What a leaked token allows | sending messages as your bot — **no** access to NextDNS |

> 🧠 A bot token and a NextDNS API key are completely separate credentials.
