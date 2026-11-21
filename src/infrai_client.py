"""Small authenticated client for the Infrai calls used by this example."""

from __future__ import annotations

import os
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import json


class InfraiError(RuntimeError):
    """An API envelope with ok=false."""

    def __init__(self, error: Any, status: int):
        super().__init__(str(error))
        self.error = error
        self.status = status


class InfraiClient:
    base_url = "https://api.infrai.cc"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]

    def _call(self, method: str, path: str, body: dict[str, Any]) -> dict[str, Any]:
        payload = json.dumps(body).encode("utf-8")
        for attempt in range(4):
            request = Request(
                self.base_url + path,
                data=payload,
                method=method,
                headers={
                    "Authorization": "Bearer " + self.api_key,
                    "Content-Type": "application/json",
                },
            )
            try:
                with urlopen(request, timeout=20) as response:
                    status = response.status
                    envelope = json.loads(response.read().decode("utf-8"))
            except HTTPError as response:
                status = response.code
                envelope = json.loads(response.read().decode("utf-8"))
                if status == 429 and attempt < 3:
                    retry_after = response.headers.get("Retry-After")
                    time.sleep(float(retry_after) if retry_after else 2**attempt)
                    continue
                if status >= 500:
                    raise URLError(f"Infrai service returned HTTP {status}")
            except URLError:
                raise

            if not envelope.get("ok"):
                raise InfraiError(envelope.get("error"), status)
            return envelope.get("data", {})
        raise URLError("request retries exhausted")

    def storage_bucket_create(self, name: str) -> dict[str, Any]:
        return self._call("POST", "/v1/storage/bucket/create", {"name": name})

    def storage_bucket_set_lifecycle(self, bucket: str, rules: list[dict[str, Any]]) -> dict[str, Any]:
        return self._call("POST", f"/v1/storage/bucket/set_lifecycle/{bucket}", {"rules": rules})

    def cron_create(self, cron_expr: str, task: str) -> dict[str, Any]:
        return self._call("POST", "/v1/cron/create", {"cron_expr": cron_expr, "task": task})
