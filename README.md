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

## Quickstart

```python
from keyhaven import Keyhaven

async with Keyhaven(base_url="https://your-keyhaven-host", api_key="<your-api-key>") as kh:
    # 1. Start an OAuth connection for one of your users
    auth_url = await kh.connect("gmail", owner_id="user_123")
    #    → the user visits auth_url and consents; Keyhaven stores encrypted credentials

    # 2. Execute a tool on their behalf — anytime
    result = await kh.execute(
        "gmail.send_email",
        owner_id="user_123",
        args={"to": "boss@company.com", "subject": "Status", "body": "All good"},
    )
```

Sync variants (`connect_sync`, `execute_sync`, …) are available for non-async code.

## Links

- Issues & docs: https://github.com/Joselma-Jemk/keyhaven-sdk

---

*Client SDK — MIT. The Keyhaven server is a separate, proprietary component.*
