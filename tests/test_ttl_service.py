from datetime import datetime, timezone

from src.ttl_service import BuildArtifact, should_expire


def test_released_build_expires_after_its_retention_window():
    artifact = BuildArtifact("build-184", datetime(2026, 1, 1, tzinfo=timezone.utc), keep_days=7)

    assert should_expire(artifact, datetime(2026, 1, 8, tzinfo=timezone.utc)) is True
    assert should_expire(artifact, datetime(2026, 1, 7, 23, 59, tzinfo=timezone.utc)) is False
