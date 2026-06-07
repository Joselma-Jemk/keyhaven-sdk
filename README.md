<div align="center">

# Keyhaven SDK

**The open-source Python client for [Keyhaven](https://github.com/Joselma-Jemk) — OAuth & tool-calling for AI agents.**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/Joselma-Jemk/keyhaven-sdk/blob/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/keyhaven.svg)](https://pypi.org/project/keyhaven/)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)

</div>

> *key + haven* — a safe harbour for the keys your agents act through.

---

## What is this?

Keyhaven is the OAuth + tool-calling layer for AI agents: your users connect their
SaaS apps once, and your agents act on their behalf — through a per-tenant encrypted
credential vault you never have to build.

This package is the **client SDK** (MIT). It talks over HTTP to a Keyhaven server.
The server core is operated as a managed service (or self-hosted by the project owner);
you only need this SDK and an API key.

## Install

```bash
pip install keyhaven
```

## Quickstart — connect Google once, use every Gmail tool

```python
import asyncio
from keyhaven import Keyhaven

OWNER = "user_123"  # your end-user's id — stable and permanent

async def main():
    async with Keyhaven(base_url="https://your-keyhaven-host", api_key="<your-api-key>") as kh:

        # ── 1. Connect Google ONCE (a single OAuth consent) ──────────────────
        # "gmail" resolves to the shared "google" connection. Ask for the scopes
        # your tools need; the user consents a single time.
        auth_url = await kh.connect(
            "gmail",
            owner_id=OWNER,
            scopes=["https://www.googleapis.com/auth/gmail.modify"],
            post_redirect="https://your-app.com/after-connect",
        )
        print("Send the user here to grant access:", auth_url)
        # → the user visits auth_url and consents. Keyhaven stores the encrypted
        #   tokens in its per-tenant vault, keyed by the PROVIDER ("google").

        # ── 2. From now on, call ANY Gmail tool — no reconnection ────────────
        # Every call for this owner reuses the stored Google connection.
        unread = await kh.execute(
            "gmail.search_emails",
            owner_id=OWNER,
            args={"query": "is:unread from:boss@company.com"},
        )

        await kh.execute(
            "gmail.send_email",
            owner_id=OWNER,
            args={"to": "boss@company.com", "subject": "Status", "body": "All good"},
        )

        await kh.execute(
            "gmail.create_draft",
            owner_id=OWNER,
            args={"to": "team@company.com", "subject": "Notes", "body": "WIP"},
        )

asyncio.run(main())
```

### One consent → every Google tool

Connections are keyed by **provider**, not by app. So the single Google consent above
also powers **Calendar, Drive, Docs, Sheets…** for that owner — no second OAuth flow.
Just request those scopes at connect time (or reconnect to add scopes incrementally;
already-granted scopes are preserved):

```python
await kh.connect("google", owner_id=OWNER, scopes=[
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar.events",
])
# now gmail.* AND google_calendar.* both work for OWNER — one connection.
```

### Ergonomic typed access

```python
# Same calls, fully type-checked, via the generated namespaces:
await kh.apps.gmail.send_email(owner_id=OWNER, to="boss@company.com",
                               subject="Status", body="All good")
```

Sync variants (`connect_sync`, `execute_sync`, …) are available for non-async code.

## Links

- Issues & docs: https://github.com/Joselma-Jemk/keyhaven-sdk

---

*Client SDK — MIT. The Keyhaven server is a separate, proprietary component.*
