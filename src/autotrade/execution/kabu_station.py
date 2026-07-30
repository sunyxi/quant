from __future__ import annotations

import json
import socket
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlencode, urlparse, urlunparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from autotrade.core.models import Market, OrderIntent, OrderStyle, Side
from autotrade.execution.ledger import LocalExecutionLedger
from autotrade.execution.oms import OrderStateMachine
from autotrade.execution.reconciliation import (
    BrokerOrderSnapshot,
    BrokerPositionSnapshot,
    BrokerStateSnapshot,
    ReconciliationEngine,
    ReconciliationReport,
)
from autotrade.risk.manager import RiskManager


class KabuStationClientError(RuntimeError):
    pass


class KabuStationAuthError(KabuStationClientError):
    pass


class KabuStationRateLimitError(KabuStationClientError):
    pass


class KabuStationServerError(KabuStationClientError):
    pass


class KabuStationTransportConnectionError(KabuStationClientError):
    pass


class KabuStationTransportTimeoutError(KabuStationClientError):
    pass


class KabuStationTransportPolicyError(KabuStationClientError):
    pass


class KabuStationTransportSystemError(KabuStationClientError):
    pass


class KabuStationTransportResponseError(KabuStationClientError):
    pass


class KabuStationMappingError(ValueError):
    pass


@dataclass(frozen=True)
class KabuStationJsonResponse:
    status_code: int
    payload: Any


class JsonPostResponse(Protocol):
    status_code: int
    payload: Any


class JsonPostTransport(Protocol):
    def post_json(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> JsonPostResponse:
        ...


class JsonPutTransport(Protocol):
    def put_json(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> JsonPostResponse:
        ...


class JsonGetTransport(Protocol):
    def get_json(
        self,
        url: str,
        query: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> JsonPostResponse:
        ...


class KabuStationTokenSource(Protocol):
    def fetch_token(self, api_password: str) -> str:
        ...


class KabuStationReadOnlySource(Protocol):
    def get_orders(
        self,
        api_token: str,
        product: str | None = None,
        symbol: str | None = None,
        details: bool | None = None,
    ) -> list[dict[str, Any]]:
        ...

    def get_positions(
        self,
        api_token: str,
        product: str | None = None,
        symbol: str | None = None,
    ) -> list[dict[str, Any]]:
        ...


class KabuStationSnapshotMapperSource(Protocol):
    def to_broker_state_snapshot(
        self,
        *,
        orders: list[dict[str, Any]],
        positions: list[dict[str, Any]],
    ) -> BrokerStateSnapshot:
        ...


@dataclass(frozen=True)
class KabuStationEnvironment:
    base_url: str

    @classmethod
    def production(cls) -> KabuStationEnvironment:
        return cls(base_url="http://localhost:18080")

    @classmethod
    def test(cls) -> KabuStationEnvironment:
        return cls(base_url="http://localhost:18081")

    @property
    def token_url(self) -> str:
        return f"{self.base_url}/kabusapi/token"

    @property
    def sendorder_url(self) -> str:
        return f"{self.base_url}/kabusapi/sendorder"

    @property
    def cancelorder_url(self) -> str:
        return f"{self.base_url}/kabusapi/cancelorder"

    @property
    def orders_url(self) -> str:
        return f"{self.base_url}/kabusapi/orders"

    @property
    def positions_url(self) -> str:
        return f"{self.base_url}/kabusapi/positions"


@dataclass(frozen=True)
class KabuStationReadOnlyHttpPolicy:
    allowed_readonly_paths: frozenset[str] = frozenset(
        {"/kabusapi/orders", "/kabusapi/positions"}
    )
    token_path: str = "/kabusapi/token"
    forbidden_mutating_paths: frozenset[str] = frozenset(
        {"/kabusapi/sendorder", "/kabusapi/cancelorder"}
    )

    def __call__(self, method: str, url: str) -> None:
        parsed = urlparse(url)
        if unquote(parsed.path) != parsed.path:
            raise KabuStationTransportPolicyError(
                "kabu Station localhost read-only policy rejects percent-encoded endpoint paths"
            )
        path = parsed.path.rstrip("/") or "/"
        normalized_method = method.upper()
        if path in self.forbidden_mutating_paths:
            raise KabuStationTransportPolicyError(
                "kabu Station localhost read-only policy rejects mutating broker endpoints"
            )
        if path == self.token_path and normalized_method == "POST":
            return
        if path in self.allowed_readonly_paths and normalized_method == "GET":
            return
        raise KabuStationTransportPolicyError(
            "kabu Station localhost read-only policy only allows token authentication and read-only orders/positions requests"
        )


class _LoopbackRedirectHandler(HTTPRedirectHandler):
    def __init__(
        self,
        policy: Callable[[str, str], None] = KabuStationReadOnlyHttpPolicy(),
    ) -> None:
        super().__init__()
        self.policy = policy

    def redirect_request(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> Request | None:
        KabuStationLocalhostHttpTransport.validate_localhost_url(newurl)
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is not None:
            self.policy(redirected.get_method(), redirected.full_url)
        return redirected


@dataclass(frozen=True)
class KabuStationLocalhostHttpTransport:
    timeout_seconds: float = 5.0
    opener: Any | None = None
    policy: Callable[[str, str], None] = KabuStationReadOnlyHttpPolicy()
    _effective_opener: Any = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        opener = self.opener or build_opener(_LoopbackRedirectHandler(self.policy))
        object.__setattr__(self, "_effective_opener", opener)

    def post_json(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> KabuStationJsonResponse:
        return self._request_json(
            method="POST",
            url=url,
            payload=payload,
            headers=headers,
        )

    def put_json(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> KabuStationJsonResponse:
        return self._request_json(
            method="PUT",
            url=url,
            payload=payload,
            headers=headers,
        )

    def get_json(
        self,
        url: str,
        query: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> KabuStationJsonResponse:
        request_url = self._url_with_query(url, query)
        return self._request_json(
            method="GET",
            url=request_url,
            payload=None,
            headers=headers,
        )

    def _request_json(
        self,
        *,
        method: str,
        url: str,
        payload: dict[str, Any] | None,
        headers: dict[str, str] | None,
    ) -> KabuStationJsonResponse:
        self.validate_localhost_url(url)
        self.policy(method, url)
        request_headers = dict(headers or {})
        data: bytes | None = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")

        request = Request(url, data=data, headers=request_headers, method=method)
        try:
            with self._effective_opener.open(
                request, timeout=self.timeout_seconds
            ) as response:
                return KabuStationJsonResponse(
                    status_code=getattr(response, "status", response.getcode()),
                    payload=self._parse_json_response(response.read()),
                )
        except HTTPError as exc:
            if 300 <= exc.code < 400:
                raise KabuStationClientError(
                    "kabu Station localhost HTTP redirect was rejected"
                ) from exc
            body = exc.read()
            try:
                payload = self._parse_json_response(body) if body else {}
            except KabuStationTransportResponseError:
                payload = {}
            return KabuStationJsonResponse(
                status_code=exc.code,
                payload=payload,
            )
        except socket.timeout as exc:
            raise KabuStationTransportTimeoutError(
                "kabu Station localhost HTTP transport timed out"
            ) from exc
        except URLError as exc:
            reason = getattr(exc, "reason", None)
            if isinstance(reason, socket.timeout):
                raise KabuStationTransportTimeoutError(
                    "kabu Station localhost HTTP transport timed out"
                ) from exc
            if isinstance(reason, ConnectionError):
                raise KabuStationTransportConnectionError(
                    "kabu Station localhost HTTP transport could not connect"
                ) from exc
            if isinstance(reason, OSError):
                raise KabuStationTransportSystemError(
                    "kabu Station localhost HTTP transport encountered an operating system error"
                ) from exc
            raise KabuStationTransportSystemError(
                "kabu Station localhost HTTP transport encountered a transport error"
            ) from exc
        except OSError as exc:
            if not isinstance(exc, ConnectionError):
                raise KabuStationTransportSystemError(
                    "kabu Station localhost HTTP transport encountered an operating system error"
                ) from exc
            raise KabuStationTransportConnectionError(
                "kabu Station localhost HTTP transport could not connect"
            ) from exc

    @staticmethod
    def _url_with_query(url: str, query: dict[str, str] | None) -> str:
        if not query:
            return url
        parsed = urlparse(url)
        encoded_query = urlencode(query)
        return urlunparse(parsed._replace(query=encoded_query))

    @staticmethod
    def validate_localhost_url(url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "http":
            raise KabuStationTransportPolicyError(
                "kabu Station localhost HTTP transport only supports http URLs"
            )
        if parsed.username is not None or parsed.password is not None:
            raise KabuStationTransportPolicyError(
                "kabu Station localhost HTTP transport rejects userinfo URLs"
            )
        if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise KabuStationTransportPolicyError(
                "kabu Station localhost HTTP transport only supports localhost URLs"
            )

    @staticmethod
    def _parse_json_response(body: bytes) -> Any:
        if not body:
            raise KabuStationTransportResponseError(
                "kabu Station localhost HTTP response body was empty"
            )
        try:
            return json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise KabuStationTransportResponseError(
                "kabu Station localhost HTTP response was not valid JSON"
            ) from exc


KABU_STATION_PROBE_SCHEMA_VERSION = "1"


@dataclass(frozen=True)
class KabuStationReadOnlyProbeResult:
    schema_version: str
    environment: str
    localhost_endpoint: str
    connection_status: str
    authentication_status: str
    orders_payload_status: str
    positions_payload_status: str
    snapshot_mapping_status: str
    order_count: int
    position_count: int
    timestamp: str
    sanitized_failure_category: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "environment": self.environment,
            "localhost_endpoint": self.localhost_endpoint,
            "connection_status": self.connection_status,
            "authentication_status": self.authentication_status,
            "orders_payload_status": self.orders_payload_status,
            "positions_payload_status": self.positions_payload_status,
            "snapshot_mapping_status": self.snapshot_mapping_status,
            "order_count": self.order_count,
            "position_count": self.position_count,
            "timestamp": self.timestamp,
            "sanitized_failure_category": self.sanitized_failure_category,
        }


@dataclass(frozen=True)
class KabuStationReadOnlyProbe:
    environment_name: str
    environment: KabuStationEnvironment
    token_client: KabuStationTokenSource
    readonly_client: KabuStationReadOnlySource
    mapper: KabuStationSnapshotMapperSource | None = None
    clock: Callable[[], datetime] = lambda: datetime.now(UTC)

    def run(self, api_password: str) -> KabuStationReadOnlyProbeResult:
        timestamp = self.clock().astimezone(UTC).isoformat()
        connection_status = "not-run"
        authentication_status = "not-run"
        orders_payload_status = "not-run"
        positions_payload_status = "not-run"
        snapshot_mapping_status = "not-run"
        order_count = 0
        position_count = 0
        failure_category: str | None = None

        try:
            api_token = self.token_client.fetch_token(api_password)
            connection_status = "ok"
            authentication_status = "ok"
        except KabuStationTransportConnectionError:
            connection_status = "failed"
            authentication_status = "not-run"
            failure_category = "connection"
            return self._result(
                timestamp,
                connection_status,
                authentication_status,
                orders_payload_status,
                positions_payload_status,
                snapshot_mapping_status,
                order_count,
                position_count,
                failure_category,
            )
        except KabuStationTransportTimeoutError:
            connection_status = "failed"
            authentication_status = "not-run"
            failure_category = "timeout"
            return self._result(
                timestamp,
                connection_status,
                authentication_status,
                orders_payload_status,
                positions_payload_status,
                snapshot_mapping_status,
                order_count,
                position_count,
                failure_category,
            )
        except KabuStationTransportPolicyError:
            connection_status = "not-run"
            authentication_status = "not-run"
            failure_category = "configuration"
            return self._result(
                timestamp,
                connection_status,
                authentication_status,
                orders_payload_status,
                positions_payload_status,
                snapshot_mapping_status,
                order_count,
                position_count,
                failure_category,
            )
        except KabuStationTransportSystemError:
            connection_status = "not-run"
            authentication_status = "not-run"
            failure_category = "system"
            return self._result(
                timestamp,
                connection_status,
                authentication_status,
                orders_payload_status,
                positions_payload_status,
                snapshot_mapping_status,
                order_count,
                position_count,
                failure_category,
            )
        except KabuStationTransportResponseError:
            connection_status = "ok"
            authentication_status = "not-run"
            failure_category = "response"
            return self._result(
                timestamp,
                connection_status,
                authentication_status,
                orders_payload_status,
                positions_payload_status,
                snapshot_mapping_status,
                order_count,
                position_count,
                failure_category,
            )
        except KabuStationClientError:
            connection_status = "ok"
            authentication_status = "failed"
            failure_category = "authentication"
            return self._result(
                timestamp,
                connection_status,
                authentication_status,
                orders_payload_status,
                positions_payload_status,
                snapshot_mapping_status,
                order_count,
                position_count,
                failure_category,
            )

        try:
            orders = self.readonly_client.get_orders(api_token=api_token)
            order_count = len(orders)
            orders_payload_status = "ok"
        except KabuStationTransportPolicyError:
            orders_payload_status = "failed"
            failure_category = "configuration"
            return self._result(
                timestamp,
                connection_status,
                authentication_status,
                orders_payload_status,
                positions_payload_status,
                snapshot_mapping_status,
                order_count,
                position_count,
                failure_category,
            )
        except KabuStationTransportConnectionError:
            orders_payload_status = "failed"
            failure_category = "connection"
            return self._result(
                timestamp,
                connection_status,
                authentication_status,
                orders_payload_status,
                positions_payload_status,
                snapshot_mapping_status,
                order_count,
                position_count,
                failure_category,
            )
        except KabuStationTransportTimeoutError:
            orders_payload_status = "failed"
            failure_category = "timeout"
            return self._result(
                timestamp,
                connection_status,
                authentication_status,
                orders_payload_status,
                positions_payload_status,
                snapshot_mapping_status,
                order_count,
                position_count,
                failure_category,
            )
        except KabuStationTransportSystemError:
            orders_payload_status = "failed"
            failure_category = "system"
            return self._result(
                timestamp,
                connection_status,
                authentication_status,
                orders_payload_status,
                positions_payload_status,
                snapshot_mapping_status,
                order_count,
                position_count,
                failure_category,
            )
        except KabuStationClientError:
            orders_payload_status = "failed"
            failure_category = "orders"
            return self._result(
                timestamp,
                connection_status,
                authentication_status,
                orders_payload_status,
                positions_payload_status,
                snapshot_mapping_status,
                order_count,
                position_count,
                failure_category,
            )

        try:
            positions = self.readonly_client.get_positions(api_token=api_token)
            position_count = len(positions)
            positions_payload_status = "ok"
        except KabuStationTransportPolicyError:
            positions_payload_status = "failed"
            failure_category = "configuration"
            return self._result(
                timestamp,
                connection_status,
                authentication_status,
                orders_payload_status,
                positions_payload_status,
                snapshot_mapping_status,
                order_count,
                position_count,
                failure_category,
            )
        except KabuStationTransportConnectionError:
            positions_payload_status = "failed"
            failure_category = "connection"
            return self._result(
                timestamp,
                connection_status,
                authentication_status,
                orders_payload_status,
                positions_payload_status,
                snapshot_mapping_status,
                order_count,
                position_count,
                failure_category,
            )
        except KabuStationTransportTimeoutError:
            positions_payload_status = "failed"
            failure_category = "timeout"
            return self._result(
                timestamp,
                connection_status,
                authentication_status,
                orders_payload_status,
                positions_payload_status,
                snapshot_mapping_status,
                order_count,
                position_count,
                failure_category,
            )
        except KabuStationTransportSystemError:
            positions_payload_status = "failed"
            failure_category = "system"
            return self._result(
                timestamp,
                connection_status,
                authentication_status,
                orders_payload_status,
                positions_payload_status,
                snapshot_mapping_status,
                order_count,
                position_count,
                failure_category,
            )
        except KabuStationClientError:
            positions_payload_status = "failed"
            failure_category = "positions"
            return self._result(
                timestamp,
                connection_status,
                authentication_status,
                orders_payload_status,
                positions_payload_status,
                snapshot_mapping_status,
                order_count,
                position_count,
                failure_category,
            )

        try:
            (self.mapper or KabuStationSnapshotMapper()).to_broker_state_snapshot(
                orders=orders,
                positions=positions,
            )
            snapshot_mapping_status = "ok"
        except KabuStationClientError:
            snapshot_mapping_status = "failed"
            failure_category = "snapshot_mapping"

        return self._result(
            timestamp,
            connection_status,
            authentication_status,
            orders_payload_status,
            positions_payload_status,
            snapshot_mapping_status,
            order_count,
            position_count,
            failure_category,
        )

    def _result(
        self,
        timestamp: str,
        connection_status: str,
        authentication_status: str,
        orders_payload_status: str,
        positions_payload_status: str,
        snapshot_mapping_status: str,
        order_count: int,
        position_count: int,
        sanitized_failure_category: str | None,
    ) -> KabuStationReadOnlyProbeResult:
        return KabuStationReadOnlyProbeResult(
            schema_version=KABU_STATION_PROBE_SCHEMA_VERSION,
            environment=self.environment_name,
            localhost_endpoint=self.environment.base_url,
            connection_status=connection_status,
            authentication_status=authentication_status,
            orders_payload_status=orders_payload_status,
            positions_payload_status=positions_payload_status,
            snapshot_mapping_status=snapshot_mapping_status,
            order_count=order_count,
            position_count=position_count,
            timestamp=timestamp,
            sanitized_failure_category=sanitized_failure_category,
        )


@dataclass(frozen=True)
class KabuStationProbeReportWriter:
    def write(
        self,
        path: str | Path,
        result: KabuStationReadOnlyProbeResult,
        *,
        overwrite: bool = False,
    ) -> Path:
        output_path = Path(path)
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            mode = "w" if overwrite else "x"
            with output_path.open(mode, encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True
                    )
                    + "\n"
                )
        except FileExistsError as exc:
            if output_path.exists():
                raise KabuStationClientError(
                    "kabu Station probe report already exists"
                ) from exc
            raise KabuStationClientError(
                "could not write kabu Station probe report"
            ) from exc
        except KabuStationClientError:
            raise
        except OSError as exc:
            raise KabuStationClientError(
                "could not write kabu Station probe report"
            ) from exc
        return output_path


@dataclass(frozen=True)
class KabuStationProbeReportReader:
    def read(self, path: str | Path) -> KabuStationReadOnlyProbeResult:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if payload.get("schema_version") != KABU_STATION_PROBE_SCHEMA_VERSION:
            raise KabuStationClientError(
                "unsupported kabu Station probe report schema_version"
            )
        required = set(KabuStationReadOnlyProbeResult.__dataclass_fields__)
        if set(payload) != required:
            raise KabuStationClientError("invalid kabu Station probe report fields")
        return KabuStationReadOnlyProbeResult(**payload)


@dataclass(frozen=True)
class KabuStationTokenClient:
    environment: KabuStationEnvironment
    transport: JsonPostTransport
    mapper: KabuStationOrderMapper | None = None

    def fetch_token(self, api_password: str) -> str:
        mapper = self.mapper or KabuStationOrderMapper()
        try:
            payload = mapper.to_token_payload(api_password)
        except KabuStationMappingError as exc:
            raise KabuStationClientError(str(exc)) from exc

        response = self.transport.post_json(self.environment.token_url, payload)
        raise_for_kabu_station_status(response.status_code, "token request")
        token = response.payload.get("Token")
        if not isinstance(token, str) or not token:
            raise KabuStationClientError("token response did not include Token")
        return token


@dataclass(frozen=True)
class KabuStationSendOrderClient:
    environment: KabuStationEnvironment
    transport: JsonPostTransport
    mapper: KabuStationOrderMapper | None = None

    def submit_cash_order(self, intent: OrderIntent, api_token: str) -> str:
        if not api_token:
            raise KabuStationClientError("API token is required")

        mapper = self.mapper or KabuStationOrderMapper()
        try:
            payload = mapper.to_cash_sendorder_payload(intent)
        except KabuStationMappingError as exc:
            raise KabuStationClientError(str(exc)) from exc

        response = self.transport.post_json(
            self.environment.sendorder_url,
            payload,
            headers={"X-API-KEY": api_token},
        )
        raise_for_kabu_station_status(response.status_code, "sendorder request")
        order_id = response.payload.get("OrderId")
        if not isinstance(order_id, str) or not order_id:
            raise KabuStationClientError("sendorder response did not include OrderId")
        return order_id


@dataclass(frozen=True)
class KabuStationCancelOrderClient:
    environment: KabuStationEnvironment
    transport: JsonPutTransport

    def cancel_order(self, order_id: str, api_token: str) -> str:
        if not api_token:
            raise KabuStationClientError("API token is required")
        if not order_id:
            raise KabuStationClientError("OrderId is required")

        response = self.transport.put_json(
            self.environment.cancelorder_url,
            {"OrderId": order_id},
            headers={"X-API-KEY": api_token},
        )
        raise_for_kabu_station_status(response.status_code, "cancelorder request")
        cancelled_order_id = response.payload.get("OrderId")
        if not isinstance(cancelled_order_id, str) or not cancelled_order_id:
            raise KabuStationClientError("cancelorder response did not include OrderId")
        return cancelled_order_id


@dataclass(frozen=True)
class KabuStationReadOnlyClient:
    environment: KabuStationEnvironment
    transport: JsonGetTransport

    def get_orders(
        self,
        api_token: str,
        product: str | None = None,
        symbol: str | None = None,
        details: bool | None = None,
    ) -> list[dict[str, Any]]:
        query: dict[str, str] = {}
        if product is not None:
            query["product"] = product
        if symbol is not None:
            query["symbol"] = symbol
        if details is not None:
            query["details"] = "true" if details else "false"

        return self._get_list(
            operation="orders request",
            url=self.environment.orders_url,
            api_token=api_token,
            query=query,
        )

    def get_positions(
        self,
        api_token: str,
        product: str | None = None,
        symbol: str | None = None,
    ) -> list[dict[str, Any]]:
        query: dict[str, str] = {}
        if product is not None:
            query["product"] = product
        if symbol is not None:
            query["symbol"] = symbol

        return self._get_list(
            operation="positions request",
            url=self.environment.positions_url,
            api_token=api_token,
            query=query,
        )

    def _get_list(
        self,
        operation: str,
        url: str,
        api_token: str,
        query: dict[str, str],
    ) -> list[dict[str, Any]]:
        if not api_token:
            raise KabuStationClientError("API token is required")

        response = self.transport.get_json(
            url,
            query=query or None,
            headers={"X-API-KEY": api_token},
        )
        raise_for_kabu_station_status(response.status_code, operation)
        if not isinstance(response.payload, list):
            raise KabuStationClientError(
                f"kabu Station {operation} response did not include a list payload"
            )
        return response.payload


@dataclass(frozen=True)
class KabuStationSnapshotMapper:
    def to_broker_state_snapshot(
        self,
        *,
        orders: list[dict[str, Any]],
        positions: list[dict[str, Any]],
    ) -> BrokerStateSnapshot:
        return BrokerStateSnapshot(
            open_orders=[
                self._order_snapshot(order)
                for order in orders
                if self._quantity(order, "LeavesQty") > 0
            ],
            positions=[
                self._position_snapshot(position)
                for position in positions
                if self._quantity(position, "LeavesQty") != 0
            ],
        )

    def _order_snapshot(self, order: dict[str, Any]) -> BrokerOrderSnapshot:
        return BrokerOrderSnapshot(
            client_order_id=self._text(order, "ID"),
            symbol=self._jp_symbol(order),
        )

    def _position_snapshot(self, position: dict[str, Any]) -> BrokerPositionSnapshot:
        quantity = self._quantity(position, "LeavesQty")
        side = self._text(position, "Side")
        if side == "1":
            quantity = -quantity
        elif side != "2":
            raise KabuStationClientError(
                f"unsupported kabu Station position Side: {side}"
            )

        return BrokerPositionSnapshot(
            symbol=self._jp_symbol(position),
            quantity=quantity,
        )

    def _jp_symbol(self, payload: dict[str, Any]) -> str:
        symbol = self._text(payload, "Symbol")
        return symbol if symbol.endswith(".T") else f"{symbol}.T"

    @staticmethod
    def _text(payload: dict[str, Any], field_name: str) -> str:
        value = payload.get(field_name)
        if not isinstance(value, str) or not value:
            raise KabuStationClientError(
                f"kabu Station snapshot payload did not include {field_name}"
            )
        return value

    @staticmethod
    def _quantity(payload: dict[str, Any], field_name: str) -> int:
        value = payload.get(field_name)
        if not isinstance(value, int):
            raise KabuStationClientError(
                f"kabu Station snapshot payload did not include integer {field_name}"
            )
        return value


@dataclass(frozen=True)
class KabuStationReadOnlyReconciler:
    client: KabuStationReadOnlySource
    mapper: KabuStationSnapshotMapper | None = None
    reconciliation: ReconciliationEngine | None = None

    def reconcile(
        self,
        *,
        api_token: str,
        oms: OrderStateMachine,
        ledger: LocalExecutionLedger,
        risk_manager: RiskManager | None = None,
        product: str | None = None,
        symbol: str | None = None,
        details: bool | None = None,
    ) -> ReconciliationReport:
        orders = self.client.get_orders(
            api_token=api_token,
            product=product,
            symbol=symbol,
            details=details,
        )
        positions = self.client.get_positions(
            api_token=api_token,
            product=product,
            symbol=symbol,
        )
        broker = (self.mapper or KabuStationSnapshotMapper()).to_broker_state_snapshot(
            orders=orders,
            positions=positions,
        )
        return (self.reconciliation or ReconciliationEngine()).check(
            oms=oms,
            ledger=ledger,
            broker=broker,
            risk_manager=risk_manager,
        )


def raise_for_kabu_station_status(status_code: int, operation: str) -> None:
    if status_code == 200:
        return
    if status_code in {401, 403}:
        raise KabuStationAuthError(f"kabu Station {operation} was unauthorized")
    if status_code == 429:
        raise KabuStationRateLimitError(f"kabu Station {operation} was rate limited")
    if status_code >= 500:
        raise KabuStationServerError(f"kabu Station {operation} failed server-side")
    raise KabuStationClientError(
        f"kabu Station {operation} failed with status {status_code}"
    )


@dataclass(frozen=True)
class KabuStationOrderMapper:
    exchange: str = "TSE"
    official_exchange: int = 27
    account_type: int = 4
    buy_fund_type: str = "02"
    expire_day: int = 0

    def to_order_payload(self, intent: OrderIntent) -> dict[str, Any]:
        if intent.market != Market.JP:
            raise KabuStationMappingError("kabu Station mapper only supports JP market")
        if intent.quantity % 100 != 0:
            raise KabuStationMappingError("JP equity quantity must be a 100 share lot")

        symbol = self._symbol_code(intent.symbol)
        return {
            "symbol": symbol,
            "exchange": self.exchange,
            "side": self._side(intent.side),
            "quantity": intent.quantity,
            "order_type": self._order_type(intent.order_style),
            "limit_price": intent.limit_price,
            "client_order_id": intent.client_order_id,
        }

    def to_token_payload(self, api_password: str) -> dict[str, str]:
        if not api_password:
            raise KabuStationMappingError("API password is required")
        return {"APIPassword": api_password}

    def to_cash_sendorder_payload(self, intent: OrderIntent) -> dict[str, Any]:
        if intent.market != Market.JP:
            raise KabuStationMappingError("kabu Station mapper only supports JP market")
        if intent.quantity % 100 != 0:
            raise KabuStationMappingError("JP equity quantity must be a 100 share lot")

        return {
            "Symbol": self._symbol_code(intent.symbol),
            "Exchange": self.official_exchange,
            "SecurityType": 1,
            "Side": self._official_side(intent.side),
            "CashMargin": 1,
            "DelivType": self._cash_delivery_type(intent.side),
            "FundType": self._cash_fund_type(intent.side),
            "AccountType": self.account_type,
            "Qty": intent.quantity,
            "FrontOrderType": self._official_front_order_type(intent.order_style),
            "Price": intent.limit_price,
            "ExpireDay": self.expire_day,
        }

    @staticmethod
    def _symbol_code(symbol: str) -> str:
        if not symbol.endswith(".T"):
            raise KabuStationMappingError("JP symbol must use .T suffix")

        code = symbol[:-2]
        if not code:
            raise KabuStationMappingError("JP symbol code is required")
        return code

    @staticmethod
    def _side(side: Side) -> str:
        if side == Side.BUY:
            return "BUY"
        if side == Side.SELL:
            return "SELL"
        raise KabuStationMappingError(f"unsupported side: {side}")

    @staticmethod
    def _official_side(side: Side) -> str:
        if side == Side.BUY:
            return "2"
        if side == Side.SELL:
            return "1"
        raise KabuStationMappingError(f"unsupported side: {side}")

    @staticmethod
    def _cash_delivery_type(side: Side) -> int:
        if side == Side.BUY:
            return 2
        if side == Side.SELL:
            return 0
        raise KabuStationMappingError(f"unsupported side: {side}")

    def _cash_fund_type(self, side: Side) -> str:
        if side == Side.BUY:
            return self.buy_fund_type
        if side == Side.SELL:
            return "  "
        raise KabuStationMappingError(f"unsupported side: {side}")

    @staticmethod
    def _order_type(order_style: OrderStyle) -> str:
        if order_style in {OrderStyle.PASSIVE_LIMIT, OrderStyle.AGGRESSIVE_LIMIT}:
            return "LIMIT"
        raise KabuStationMappingError(
            f"unsupported order style for kabu Station mapper: {order_style}"
        )

    @staticmethod
    def _official_front_order_type(order_style: OrderStyle) -> int:
        if order_style in {OrderStyle.PASSIVE_LIMIT, OrderStyle.AGGRESSIVE_LIMIT}:
            return 20
        raise KabuStationMappingError(
            f"unsupported order style for kabu Station mapper: {order_style}"
        )
