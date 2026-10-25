import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlsplit

import pytest

from budgetgate import (
    PrometheusError,
    remaining_budget_from_prometheus,
    remaining_budget_from_sli,
)
from budgetgate.prometheus import query_sli


def _vector(*values):
    return {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [{"metric": {}, "value": [1.7e9, v]} for v in values],
        },
    }


@pytest.fixture
def prom():
    """A real local HTTP server; set .status and .body per test, read .requests after."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            server.requests.append((urlsplit(self.path), dict(self.headers)))
            payload = (
                server.body if isinstance(server.body, bytes) else json.dumps(server.body).encode()
            )
            self.send_response(server.status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    server.status, server.body, server.requests = 200, _vector("0.995"), []
    server.url = f"http://127.0.0.1:{server.server_port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()


def test_sli_to_budget_math():
    # 99% target allows 1% bad. A 99.5% SLI has used half of it.
    assert remaining_budget_from_sli(0.995, 0.99) == pytest.approx(0.5)
    assert remaining_budget_from_sli(1.0, 0.99) == 1.0
    assert remaining_budget_from_sli(0.98, 0.99) == 0.0  # overspent clamps to 0


@pytest.mark.parametrize("sli", [-0.1, 1.01, float("nan")])
def test_sli_outside_unit_interval_raises(sli):
    with pytest.raises(ValueError):
        remaining_budget_from_sli(sli, 0.99)


@pytest.mark.parametrize("slo", [0.0, 1.0, 1.5])
def test_slo_target_checked(slo):
    with pytest.raises(ValueError):
        remaining_budget_from_sli(0.99, slo)


def test_budget_from_live_query(prom):
    budget = remaining_budget_from_prometheus(
        prom.url, "sum(rate(ok[30d]))/sum(rate(all[30d]))", 0.99
    )

    assert budget == pytest.approx(0.5)
    url, _ = prom.requests[0]
    assert url.path == "/api/v1/query"
    assert parse_qs(url.query)["query"] == ["sum(rate(ok[30d]))/sum(rate(all[30d]))"]


def test_headers_are_sent(prom):
    query_sli(prom.url, "up", headers={"Authorization": "Bearer example-token"})

    assert prom.requests[0][1]["Authorization"] == "Bearer example-token"


def test_trailing_slash_in_base_url(prom):
    assert query_sli(prom.url + "/", "up") == pytest.approx(0.995)


def test_scalar_result(prom):
    prom.body = {"status": "success", "data": {"resultType": "scalar", "result": [1.7e9, "0.999"]}}

    assert query_sli(prom.url, "scalar(up)") == pytest.approx(0.999)


def test_no_data_raises(prom):
    prom.body = _vector()

    with pytest.raises(PrometheusError, match="exactly one sample, got 0"):
        query_sli(prom.url, "up")


def test_several_series_raise(prom):
    prom.body = _vector("0.99", "0.98")

    with pytest.raises(PrometheusError, match="sum"):
        query_sli(prom.url, "up")


@pytest.mark.parametrize("value", ["NaN", "+Inf", "-Inf", "not-a-number"])
def test_unusable_value_raises(prom, value):
    prom.body = _vector(value)

    with pytest.raises(PrometheusError):
        query_sli(prom.url, "up")


def test_matrix_result_is_rejected(prom):
    prom.body = {"status": "success", "data": {"resultType": "matrix", "result": []}}

    with pytest.raises(PrometheusError, match="instant query"):
        query_sli(prom.url, "up[5m]")


def test_error_status_in_body_raises(prom):
    prom.status = 400
    prom.body = {"status": "error", "errorType": "bad_data", "error": "parse error"}

    with pytest.raises(PrometheusError, match="400"):
        query_sli(prom.url, "(")


def test_failure_status_in_a_200_body_raises(prom):
    prom.body = {"status": "error", "error": "query timed out"}

    with pytest.raises(PrometheusError, match="query timed out"):
        query_sli(prom.url, "up")


def test_non_json_body_raises(prom):
    prom.body = b"<html>bad gateway</html>"

    with pytest.raises(PrometheusError):
        query_sli(prom.url, "up")


def test_sli_above_one_from_server_is_an_error_not_full_budget(prom):
    prom.body = _vector("1.2")

    with pytest.raises(ValueError):
        remaining_budget_from_prometheus(prom.url, "up", 0.99)


def test_unreachable_server_raises():
    with pytest.raises(PrometheusError):
        query_sli("http://127.0.0.1:1", "up", timeout=1)


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://example.com", "prometheus:9090"])
def test_only_http_urls_are_accepted(url):
    with pytest.raises(ValueError, match="http"):
        query_sli(url, "up")
