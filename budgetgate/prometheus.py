"""Prometheus budget adapter: read an SLI from a PromQL query and turn it into a budget.

Standard library only. The query should return the SLI as a ratio between 0 and 1,
for example the share of non-5xx responses over the SLO window:

    sum(rate(http_requests_total{job="checkout",code!~"5.."}[30d]))
      / sum(rate(http_requests_total{job="checkout"}[30d]))

Any failure to get one clean number raises ``PrometheusError``. The adapter never
guesses a budget: pass the error on, or hand ``evaluate`` ``float("nan")``, which
requires a human.
"""

import json
import math
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping

from .budget import remaining_budget_from_sli


class PrometheusError(RuntimeError):
    """The query failed, or its answer is not a single usable number."""


def query_sli(
    base_url: str,
    query: str,
    *,
    timeout: float = 10.0,
    headers: Mapping[str, str] | None = None,
) -> float:
    """Run an instant query against ``<base_url>/api/v1/query`` and return its one value.

    The query must produce exactly one sample. Zero samples means no data, several
    means the query needs ``sum(...)``; both raise ``PrometheusError``, as does a
    non-finite value (``0/0`` when there is no traffic yields NaN).
    """
    scheme = urllib.parse.urlsplit(base_url).scheme
    if scheme not in ("http", "https"):
        raise ValueError(f"base_url must start with http:// or https://, got {base_url!r}")

    url = f"{base_url.rstrip('/')}/api/v1/query?{urllib.parse.urlencode({'query': query})}"
    request = urllib.request.Request(url, headers=dict(headers or {}))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            body = json.load(response)
    except urllib.error.HTTPError as exc:
        raise PrometheusError(f"Prometheus answered HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise PrometheusError(f"Prometheus query failed: {exc}") from exc

    return _single_value(body)


def remaining_budget_from_prometheus(
    base_url: str,
    query: str,
    slo_target: float,
    *,
    timeout: float = 10.0,
    headers: Mapping[str, str] | None = None,
) -> float:
    """Fraction of the error budget left, from a PromQL SLI ratio query."""
    sli = query_sli(base_url, query, timeout=timeout, headers=headers)
    return remaining_budget_from_sli(sli, slo_target)


def _single_value(body: object) -> float:
    if not isinstance(body, dict) or body.get("status") != "success":
        error = body.get("error", "no error message") if isinstance(body, dict) else body
        raise PrometheusError(f"Prometheus reported a failure: {error}")

    data = body.get("data")
    if not isinstance(data, dict):
        raise PrometheusError("Prometheus response has no data")
    result_type, result = data.get("resultType"), data.get("result")

    if result_type == "scalar":
        sample = result
    elif result_type == "vector":
        if not isinstance(result, list) or len(result) != 1:
            count = len(result) if isinstance(result, list) else "invalid"
            raise PrometheusError(
                f"query must return exactly one sample, got {count}; wrap it in sum(...)"
            )
        sample = result[0].get("value") if isinstance(result[0], dict) else None
    else:
        raise PrometheusError(f"unsupported result type {result_type!r}; use an instant query")

    try:
        value = float(sample[1])
    except (TypeError, IndexError, ValueError) as exc:
        raise PrometheusError(f"cannot read a number from sample {sample!r}") from exc
    if not math.isfinite(value):
        raise PrometheusError(f"query returned {value}; is there traffic in the window?")
    return value
