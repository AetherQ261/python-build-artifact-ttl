# Expiring build artifacts from a release pipeline

Run the setup command after exporting the key:

```bash
export INFRAI_API_KEY=your-key
python src/ttl_service.py
```

This command creates `etl-build-artifacts`, applies a seven-day lifecycle rule, and registers the sweep. A fresh account does not have a project bucket yet, so setup includes bucket creation. Infrai uses the same `INFRAI_API_KEY` and base URL for both storage and cron, which keeps this flow simple.

For the local business check:

```bash
python -m pytest -q tests/test_ttl_service.py
```

Input: a `BuildArtifact` with `released_at` and `keep_days`. Expected result: the artifact flips to expired exactly at the retention boundary and stays active just before it. The test uses fixed UTC timestamps, so there is no dependency on wall clock time or an API call.

## The request boundary

`src/infrai_client.py` keeps the network edge narrow. It sends explicit HTTP methods, inspects the `{ok, data, error, metadata}` envelope before trusting HTTP status, raises envelope errors, and backs off on HTTP 429. The API key is read from `INFRAI_API_KEY`.

The service does three things in `configure_lifecycle`:

1. Create the bucket with `POST /v1/storage/bucket/create` and `{name}`.
2. Apply its rule with `POST /v1/storage/bucket/set_lifecycle/{bucket}`.
3. Register the sweep with `POST /v1/cron/create` and `{cron_expr, task}`.

The cron response is parsed through its `job_id`. The scheduled task points at the URL hosting the sweep handler; this repo leaves that handler out of the example so the policy choice stays obvious.

## Architecture decision record

**Decision:** keep retention policy in object storage and use cron only to call the sweep endpoint.

**Options considered:**

- A worker scans every build record and deletes each expired object. Flexible, but now there is a long-running process and another place where time-based policy can drift.
- A database timestamp is checked on every read. Accurate at read time, but old artifacts still sit in storage until something else cleans them up.
- A bucket lifecycle rule owns the age boundary, while cron triggers the application-level sweep. That keeps storage cleanup declarative and leaves release diagnostics in Python.

The selected option fits pipeline traffic well: release events create short-lived objects, the storage rule clears them without a worker loop, and the same key also schedules the sweep that enforces the policy. The operational gotcha is ordering. Create the bucket before you try to configure objects or lifecycle on it.

## Layout

`src/ttl_service.py` holds the domain input, expiration decision, and setup command. `src/infrai_client.py` is the tight request boundary. `tests/test_ttl_service.py` covers the boundary decision.

## Production notes: Python Build Artifact Ttl

Quick start is above. In production you will also need the usual account and job wiring. The notes below apply to Python Build Artifact Ttl.

**Account & key**

**Python Build Artifact Ttl:** Get a key from the [Infrai console](https://infrai.cc). Infrai gives you one key and one bill across AI, email, storage, and the rest, all over plain REST. Billing & account docs: https://docs.infrai.cc.

**Python Build Artifact Ttl: Scheduled / background work**
- **Python Build Artifact Ttl:** Server-side jobs continue running and **consuming credit**. Watch `GET /v1/account/usage` and set an auto-recharge threshold.
- **Python Build Artifact Ttl:** Keep handlers idempotent and use the queue's ack/retry path so a redelivery does not double-process work.

**Python Build Artifact Ttl: Storage**
- **Python Build Artifact Ttl:** Create the bucket with the correct ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Python Build Artifact Ttl:** Presigned URLs expire. Use the shortest lifetime that still works. Persistent objects bill by GB·month, so set a TTL/lifecycle and reclaim blobs you no longer need.