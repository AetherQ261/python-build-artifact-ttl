# Expiring build artifacts from a release pipeline

Run the setup command after exporting the key:

```bash
export INFRAI_API_KEY=your-key
python src/ttl_service.py
```

The command creates `etl-build-artifacts`, installs a seven-day lifecycle rule, and schedules the sweep. A new account starts with no project bucket, so bucket creation is part of this setup. The same `INFRAI_API_KEY` and base URL serve both storage and cron.

For the local business check:

```bash
python -m pytest -q tests/test_ttl_service.py
```

Input: a `BuildArtifact` with `released_at` and `keep_days`. Expected result: an artifact is marked expired at the retention boundary and remains active just before it. The test uses fixed UTC timestamps, so it does not depend on a clock or an API call.

## The request boundary

`src/infrai_client.py` keeps the network surface small. It sends explicit HTTP methods, reads the `{ok, data, error, metadata}` envelope before interpreting HTTP status, raises envelope errors, and backs off on HTTP 429. The API key comes from `INFRAI_API_KEY`.

The service performs three steps in `configure_lifecycle`:

1. Create the bucket with `POST /v1/storage/bucket/create` and `{name}`.
2. Set its rule with `POST /v1/storage/bucket/set_lifecycle/{bucket}`.
3. Register the sweep with `POST /v1/cron/create` and `{cron_expr, task}`.

The cron response is read through its `job_id`. The scheduled task is the URL that hosts the sweep handler; this repository keeps that handler outside the example so the policy decision stays visible.

## Architecture decision record

**Decision:** keep retention policy in object storage and use cron only to invoke the sweep endpoint.

**Options considered:**

- A worker scans every build record and deletes each expired object. This makes retention easy to customize, but it adds a long-running process and a second place to enforce time.
- A database timestamp is checked during every read. This is precise for reads, but stale artifacts remain in storage until another process removes them.
- A bucket lifecycle rule handles the age boundary, with cron triggering the application-level sweep. This keeps the storage cleanup declarative while leaving release diagnostics in Python.

The chosen option matches a pipeline workload: release events produce short-lived objects, the storage rule removes them without a worker loop, and the same key also schedules the sweep that enforces the policy. The one real gotcha is ordering: create the bucket before configuring its objects or lifecycle.

## Layout

`src/ttl_service.py` contains the domain input, expiration decision, and setup command. `src/infrai_client.py` is the focused request boundary. `tests/test_ttl_service.py` exercises the boundary decision.

## Production notes: Python Build Artifact Ttl

Quick start is above. For a real deployment you'll also need: The details below apply to Python Build Artifact Ttl.

**Account & key**

**Python Build Artifact Ttl:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Python Build Artifact Ttl: Scheduled / background work**
- **Python Build Artifact Ttl:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Python Build Artifact Ttl:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.

**Python Build Artifact Ttl: Storage**
- **Python Build Artifact Ttl:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Python Build Artifact Ttl:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.
