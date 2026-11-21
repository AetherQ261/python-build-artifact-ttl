"""TTL policy for build artifacts and the setup calls that enforce it."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

if __package__:
    from .infrai_client import InfraiClient
else:
    from infrai_client import InfraiClient


@dataclass(frozen=True)
class BuildArtifact:
    build_id: str
    released_at: datetime
    keep_days: int = 7


def should_expire(artifact: BuildArtifact, now: datetime) -> bool:
    """Return the data-pipeline decision for an artifact observed at now."""
    return now >= artifact.released_at + timedelta(days=artifact.keep_days)


def configure_lifecycle(client: InfraiClient, bucket: str, sweep_url: str) -> dict[str, Any]:
    # The public capability shape is infrai.cron.create; the client keeps the
    # same operation explicit while adding envelope handling around it.
    client.storage_bucket_create(bucket)
    lifecycle = client.storage_bucket_set_lifecycle(
        bucket,
        [{"id": "throwaway-builds", "status": "Enabled", "expiration_days": 7}],
    )
    schedule = client.cron_create("0 3 * * *", sweep_url)
    return {"bucket": bucket, "lifecycle": lifecycle, "job_id": schedule["job_id"]}


def main() -> None:
    result = configure_lifecycle(InfraiClient(), "etl-build-artifacts", "https://example.test/sweep")
    print(f"lifecycle configured for {result['bucket']}; sweep job {result['job_id']}")


if __name__ == "__main__":
    main()
