from __future__ import annotations

import importlib
import json
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from types import ModuleType
from typing import Any, Protocol


MIN_MOOMOO_API_VERSION = "10.4.6408"
MOOMOO_DISCOVERY_SCHEMA_VERSION = 1
MOOMOO_PAPER_ACCOUNT_PREFLIGHT_SCHEMA_VERSION = 1
_MOOMOO_PREFLIGHT_REFRESH_CACHE = True
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
_VERSION_PATTERN = re.compile(r"\d+(?:\.\d+){2,3}")
_SERVER_VERSION_PATTERN = re.compile(r"\d+(?:\.\d+){0,3}")
_ENDPOINT_PATTERN = re.compile(r"(?:127\.0\.0\.1|localhost):\d{1,5}|\[::1\]:\d{1,5}")
MOOMOO_VALID_ENTITLEMENTS = frozenset(
    {"NO", "BMP", "LV1", "LV2", "LV3", "SF", "UNKNOWN"}
)


class MoomooClientError(RuntimeError):
    pass


class MoomooConfigurationError(MoomooClientError):
    pass


class MoomooDependencyError(MoomooClientError):
    pass


class MoomooConnectionError(MoomooClientError):
    pass


class MoomooResponseError(MoomooClientError):
    pass


@dataclass(frozen=True)
class MoomooEndpoint:
    host: str = "127.0.0.1"
    port: int = 11111

    def __post_init__(self) -> None:
        if self.host not in _LOOPBACK_HOSTS:
            raise MoomooConfigurationError(
                "Moomoo OpenD host must be a supported loopback host"
            )
        if not isinstance(self.port, int) or isinstance(self.port, bool):
            raise MoomooConfigurationError("Moomoo OpenD port must be an integer")
        if not 1 <= self.port <= 65535:
            raise MoomooConfigurationError(
                "Moomoo OpenD port must be between 1 and 65535"
            )

    @property
    def display(self) -> str:
        host = f"[{self.host}]" if ":" in self.host else self.host
        return f"{host}:{self.port}"


class MoomooQuoteContext(Protocol):
    def get_global_state(self) -> tuple[int, object]: ...

    def get_user_info(self) -> tuple[int, object]: ...

    def close(self) -> None: ...


class MoomooTradeContext(Protocol):
    def get_acc_list(self) -> tuple[int, object]: ...

    def accinfo_query(self, **kwargs: object) -> tuple[int, object]: ...

    def position_list_query(self, **kwargs: object) -> tuple[int, object]: ...

    def order_list_query(self, **kwargs: object) -> tuple[int, object]: ...

    def place_order(self, **kwargs: object) -> tuple[int, object]: ...

    def close(self) -> None: ...


class MoomooSdkSource(Protocol):
    version: str
    ret_ok: int
    simulate_trade_environment: object
    buy_trade_side: object
    normal_order_type: object
    day_time_in_force: object
    rth_session: object

    def create_quote_context(self, endpoint: MoomooEndpoint) -> MoomooQuoteContext: ...

    def create_us_trade_context(self, endpoint: MoomooEndpoint) -> MoomooTradeContext: ...


@dataclass(frozen=True)
class MoomooApiSdk:
    module: ModuleType

    @classmethod
    def load(cls) -> MoomooApiSdk:
        try:
            module = importlib.import_module("moomoo")
        except (ImportError, ModuleNotFoundError) as exc:
            raise MoomooDependencyError(
                "moomoo-api is unavailable; install the reviewed optional dependency"
            ) from exc
        except Exception as exc:
            raise MoomooDependencyError(
                "moomoo-api could not be initialized"
            ) from exc
        enable_console_log = getattr(
            getattr(module, "SysConfig", None),
            "enable_console_log",
            None,
        )
        if not callable(enable_console_log):
            raise MoomooDependencyError(
                "moomoo-api cannot disable console logging"
            )
        try:
            enable_console_log(False)
        except Exception as exc:
            raise MoomooDependencyError(
                "moomoo-api console logging could not be disabled"
            ) from exc
        return cls(module=module)

    @property
    def version(self) -> str:
        return str(getattr(self.module, "__version__", "0"))

    @property
    def ret_ok(self) -> int:
        return int(getattr(self.module, "RET_OK", 0))

    @property
    def simulate_trade_environment(self) -> object:
        try:
            return self.module.TrdEnv.SIMULATE
        except AttributeError as exc:
            raise MoomooDependencyError(
                "moomoo-api does not expose the simulated trade environment"
            ) from exc

    @property
    def buy_trade_side(self) -> object:
        return self._required_constant("TrdSide", "BUY", "buy trade side")

    @property
    def normal_order_type(self) -> object:
        return self._required_constant("OrderType", "NORMAL", "normal order type")

    @property
    def day_time_in_force(self) -> object:
        return self._required_constant("TimeInForce", "DAY", "day time in force")

    @property
    def rth_session(self) -> object:
        return self._required_constant("Session", "RTH", "RTH session")

    def _required_constant(self, group: str, name: str, label: str) -> object:
        try:
            return getattr(getattr(self.module, group), name)
        except AttributeError as exc:
            raise MoomooDependencyError(
                f"moomoo-api does not expose the {label}"
            ) from exc

    def create_quote_context(self, endpoint: MoomooEndpoint) -> MoomooQuoteContext:
        try:
            return self.module.OpenQuoteContext(
                host=endpoint.host,
                port=endpoint.port,
            )
        except Exception as exc:
            raise MoomooConnectionError(
                "could not create the local Moomoo quote context"
            ) from exc

    def create_us_trade_context(self, endpoint: MoomooEndpoint) -> MoomooTradeContext:
        try:
            return self.module.OpenSecTradeContext(
                filter_trdmarket=self.module.TrdMarket.US,
                host=endpoint.host,
                port=endpoint.port,
                security_firm=self.module.SecurityFirm.FUTUJP,
            )
        except Exception as exc:
            raise MoomooConnectionError(
                "could not create the local Moomoo US trade context"
            ) from exc


@dataclass(frozen=True)
class MoomooDiscoveryResult:
    schema_version: int = MOOMOO_DISCOVERY_SCHEMA_VERSION
    endpoint: str = "127.0.0.1:11111"
    sdk_version: str = "UNKNOWN"
    server_version: str = "UNKNOWN"
    quote_connection_status: str = "not-run"
    trade_connection_status: str = "not-run"
    qot_logged_in: bool | None = None
    trd_logged_in: bool | None = None
    us_quote_entitlement: str = "UNKNOWN"
    jp_quote_entitlement: str = "UNKNOWN"
    account_count: int = 0
    paper_account_count: int = 0
    real_account_count: int = 0
    paper_account_available: bool = False
    us_market_authorized: bool = False
    sanitized_failure_category: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class MoomooReadOnlyDiscovery:
    endpoint: MoomooEndpoint
    sdk: MoomooSdkSource

    def run(self) -> MoomooDiscoveryResult:
        raw_sdk_version = str(self.sdk.version)
        sdk_version = _safe_version(raw_sdk_version)
        if sdk_version == "UNKNOWN" or not _version_at_least(
            raw_sdk_version,
            MIN_MOOMOO_API_VERSION,
        ):
            return self._failure("version", sdk_version=sdk_version)

        quote_context: MoomooQuoteContext | None = None
        trade_context: MoomooTradeContext | None = None
        try:
            quote_context = self.sdk.create_quote_context(self.endpoint)
            global_state = self._read_payload(
                quote_context.get_global_state(),
                "global state",
            )
            user_info = self._read_payload(
                quote_context.get_user_info(),
                "quote entitlement",
            )
            if not isinstance(global_state, Mapping) or not isinstance(
                user_info, Mapping
            ):
                raise MoomooResponseError("unexpected Moomoo quote response shape")

            trade_context = self.sdk.create_us_trade_context(self.endpoint)
            account_payload = self._read_payload(
                trade_context.get_acc_list(),
                "account list",
            )
            accounts = _records(account_payload)
            paper_count = sum(
                _enum_name(_field(row, "trd_env")) == "SIMULATE"
                for row in accounts
            )
            real_count = sum(
                _enum_name(_field(row, "trd_env")) == "REAL" for row in accounts
            )
            us_authorized = any(
                "US" in _market_names(_field(row, "trdmarket_auth"))
                for row in accounts
            )

            return MoomooDiscoveryResult(
                endpoint=self.endpoint.display,
                sdk_version=sdk_version,
                server_version=_safe_server_version(global_state.get("server_ver")),
                quote_connection_status="ok",
                trade_connection_status="ok",
                qot_logged_in=_safe_bool(global_state.get("qot_logined")),
                trd_logged_in=_safe_bool(global_state.get("trd_logined")),
                us_quote_entitlement=_safe_entitlement(
                    user_info.get("us_qot_right")
                ),
                jp_quote_entitlement=_safe_entitlement(
                    user_info.get("jp_qot_right")
                ),
                account_count=len(accounts),
                paper_account_count=paper_count,
                real_account_count=real_count,
                paper_account_available=paper_count > 0,
                us_market_authorized=us_authorized,
            )
        except MoomooConnectionError:
            return self._failure("connection", sdk_version=sdk_version)
        except MoomooResponseError:
            return self._failure("response", sdk_version=sdk_version)
        except Exception:
            return self._failure("system", sdk_version=sdk_version)
        finally:
            _safe_close(trade_context)
            _safe_close(quote_context)

    def _read_payload(
        self,
        response: tuple[int, object],
        label: str,
    ) -> object:
        if not isinstance(response, tuple) or len(response) != 2:
            raise MoomooResponseError(f"unexpected Moomoo {label} response")
        status, payload = response
        if status != self.sdk.ret_ok:
            raise MoomooResponseError(f"Moomoo {label} request failed")
        return payload

    def _failure(self, category: str, *, sdk_version: str) -> MoomooDiscoveryResult:
        return MoomooDiscoveryResult(
            endpoint=self.endpoint.display,
            sdk_version=sdk_version,
            sanitized_failure_category=category,
        )


class MoomooDiscoveryReportWriter:
    def write(
        self,
        path: str | Path,
        result: MoomooDiscoveryResult,
    ) -> Path:
        return _write_create_only_report(path, result.to_dict(), "discovery")


class MoomooDiscoveryReportReader:
    def read(self, path: str | Path) -> MoomooDiscoveryResult:
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise MoomooConfigurationError(
                "could not read the Moomoo discovery report"
            ) from exc
        required = set(MoomooDiscoveryResult.__dataclass_fields__)
        if not isinstance(payload, dict) or set(payload) != required:
            raise MoomooConfigurationError("invalid Moomoo discovery report fields")
        if (
            type(payload.get("schema_version")) is not int
            or payload["schema_version"] != MOOMOO_DISCOVERY_SCHEMA_VERSION
        ):
            raise MoomooConfigurationError(
                "unsupported Moomoo discovery report schema"
            )
        _validate_report_payload(payload)
        try:
            return MoomooDiscoveryResult(**payload)
        except TypeError as exc:
            raise MoomooConfigurationError(
                "invalid Moomoo discovery report payload"
            ) from exc


class MoomooPaperReadinessSource(Protocol):
    schema_version: int

    @property
    def is_ready(self) -> bool: ...


@dataclass(frozen=True)
class MoomooPaperAccountPreflightResult:
    schema_version: int = MOOMOO_PAPER_ACCOUNT_PREFLIGHT_SCHEMA_VERSION
    endpoint: str = "127.0.0.1:11111"
    sdk_version: str = "UNKNOWN"
    readiness_schema_version: int = 0
    connection_status: str = "not-run"
    account_selection_status: str = "not-run"
    eligible_account_count: int = 0
    account_type: str = "UNKNOWN"
    sim_account_type: str = "UNKNOWN"
    account_status: str = "UNKNOWN"
    funds_query_status: str = "not-run"
    positions_query_status: str = "not-run"
    orders_query_status: str = "not-run"
    position_count: int = 0
    order_record_count: int = 0
    refresh_cache: bool = _MOOMOO_PREFLIGHT_REFRESH_CACHE
    sanitized_failure_category: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class _MoomooPreflightQueryFailure(RuntimeError):
    def __init__(self, category: str) -> None:
        super().__init__(category)
        self.category = category


@dataclass(frozen=True)
class MoomooPaperAccountPreflight:
    endpoint: MoomooEndpoint
    sdk: MoomooSdkSource

    def run(
        self,
        *,
        readiness: MoomooPaperReadinessSource,
    ) -> MoomooPaperAccountPreflightResult:
        readiness_schema_version = _safe_nonnegative_int(readiness.schema_version)
        if not readiness.is_ready:
            return self._result(
                readiness_schema_version=readiness_schema_version,
                sanitized_failure_category="readiness",
            )

        raw_sdk_version = str(self.sdk.version)
        sdk_version = _safe_version(raw_sdk_version)
        if sdk_version == "UNKNOWN" or not _version_at_least(
            raw_sdk_version,
            MIN_MOOMOO_API_VERSION,
        ):
            return self._result(
                readiness_schema_version=readiness_schema_version,
                sdk_version=sdk_version,
                sanitized_failure_category="version",
            )

        context: MoomooTradeContext | None = None
        state: dict[str, object] = {
            "readiness_schema_version": readiness_schema_version,
            "sdk_version": sdk_version,
        }
        try:
            context = self.sdk.create_us_trade_context(self.endpoint)
            state["connection_status"] = "ok"
            accounts = _records(self._read_payload(context.get_acc_list(), "account"))
            eligible = [
                row for row in accounts if is_moomoo_us_paper_account_eligible(row)
            ]
            state["eligible_account_count"] = len(eligible)
            if len(eligible) != 1:
                state["account_selection_status"] = "blocked"
                return self._result(**state, sanitized_failure_category="account")

            account = eligible[0]
            account_id = _field(account, "acc_id")
            if not (
                isinstance(account_id, int)
                and not isinstance(account_id, bool)
                and account_id > 0
            ):
                state["account_selection_status"] = "blocked"
                return self._result(**state, sanitized_failure_category="account")

            state.update(
                account_selection_status="unique",
                account_type=_enum_name(_field(account, "acc_type")),
                sim_account_type=_enum_name(_field(account, "sim_acc_type")),
                account_status=_enum_name(_field(account, "acc_status")),
            )
            query_kwargs = {
                "trd_env": self.sdk.simulate_trade_environment,
                "acc_id": account_id,
                "refresh_cache": _MOOMOO_PREFLIGHT_REFRESH_CACHE,
            }
            self._query_records(
                lambda: context.accinfo_query(**query_kwargs),
                "funds",
            )
            state["funds_query_status"] = "ok"
            positions = self._query_records(
                lambda: context.position_list_query(**query_kwargs),
                "positions",
            )
            state["positions_query_status"] = "ok"
            state["position_count"] = len(positions)
            orders = self._query_records(
                lambda: context.order_list_query(**query_kwargs),
                "orders",
            )
            state["orders_query_status"] = "ok"
            state["order_record_count"] = len(orders)
            return self._result(**state)
        except MoomooConnectionError:
            return self._result(**state, sanitized_failure_category="connection")
        except _MoomooPreflightQueryFailure as exc:
            return self._result(
                **state,
                sanitized_failure_category=exc.category,
            )
        except MoomooResponseError:
            return self._result(**state, sanitized_failure_category="account")
        except Exception:
            return self._result(**state, sanitized_failure_category="system")
        finally:
            _safe_close(context)

    def _read_payload(self, response: tuple[int, object], category: str) -> object:
        if not isinstance(response, tuple) or len(response) != 2:
            raise _MoomooPreflightQueryFailure(category)
        status, payload = response
        if status != self.sdk.ret_ok:
            raise _MoomooPreflightQueryFailure(category)
        return payload

    def _read_records(
        self,
        response: tuple[int, object],
        category: str,
    ) -> list[object]:
        try:
            return _records(self._read_payload(response, category))
        except MoomooResponseError as exc:
            raise _MoomooPreflightQueryFailure(category) from exc

    def _query_records(
        self,
        query: Callable[[], tuple[int, object]],
        category: str,
    ) -> list[object]:
        try:
            response = query()
        except MoomooResponseError as exc:
            raise _MoomooPreflightQueryFailure(category) from exc
        return self._read_records(response, category)

    def _result(
        self,
        **changes: Any,
    ) -> MoomooPaperAccountPreflightResult:
        return replace(
            MoomooPaperAccountPreflightResult(
                endpoint=self.endpoint.display,
            ),
            **changes,
        )


class MoomooPaperAccountPreflightReportWriter:
    def write(
        self,
        path: str | Path,
        result: MoomooPaperAccountPreflightResult,
    ) -> Path:
        return _write_create_only_report(
            path,
            result.to_dict(),
            "paper-account preflight",
        )


class MoomooPaperAccountPreflightReportReader:
    def read(self, path: str | Path) -> MoomooPaperAccountPreflightResult:
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise MoomooConfigurationError(
                "could not read the Moomoo paper-account preflight report"
            ) from exc
        required = set(MoomooPaperAccountPreflightResult.__dataclass_fields__)
        if not isinstance(payload, dict) or set(payload) != required:
            raise MoomooConfigurationError(
                "invalid Moomoo paper-account preflight report fields"
            )
        _validate_preflight_report_payload(payload)
        return MoomooPaperAccountPreflightResult(**payload)


def _write_create_only_report(
    path: str | Path,
    payload: Mapping[str, object],
    label: str,
) -> Path:
    output_path = Path(path)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("x", encoding="utf-8") as stream:
            json.dump(payload, stream, sort_keys=True)
            stream.write("\n")
    except FileExistsError as exc:
        raise MoomooConfigurationError(
            f"Moomoo {label} report already exists"
        ) from exc
    except OSError as exc:
        raise MoomooConfigurationError(
            f"could not write the Moomoo {label} report"
        ) from exc
    return output_path


def _validate_preflight_report_payload(payload: Mapping[str, object]) -> None:
    if (
        type(payload.get("schema_version")) is not int
        or payload["schema_version"]
        != MOOMOO_PAPER_ACCOUNT_PREFLIGHT_SCHEMA_VERSION
    ):
        raise MoomooConfigurationError(
            "unsupported Moomoo paper-account preflight report schema"
        )
    string_fields = {
        "endpoint",
        "sdk_version",
        "connection_status",
        "account_selection_status",
        "account_type",
        "sim_account_type",
        "account_status",
        "funds_query_status",
        "positions_query_status",
        "orders_query_status",
    }
    if any(not isinstance(payload[field], str) for field in string_fields):
        raise MoomooConfigurationError(
            "invalid Moomoo paper-account preflight report payload"
        )
    if not _safe_report_endpoint(payload["endpoint"]):
        raise MoomooConfigurationError(
            "invalid Moomoo paper-account preflight report payload"
        )
    if payload["sdk_version"] != "UNKNOWN" and not _VERSION_PATTERN.fullmatch(
        payload["sdk_version"]
    ):
        raise MoomooConfigurationError(
            "invalid Moomoo paper-account preflight report payload"
        )
    allowed_values = {
        "connection_status": {"not-run", "ok"},
        "account_selection_status": {"not-run", "unique", "blocked"},
        "account_type": {"UNKNOWN", "MARGIN", "CASH"},
        "sim_account_type": {"UNKNOWN", "STOCK_AND_OPTION"},
        "account_status": {"UNKNOWN", "ACTIVE"},
        "funds_query_status": {"not-run", "ok"},
        "positions_query_status": {"not-run", "ok"},
        "orders_query_status": {"not-run", "ok"},
    }
    for field, allowed in allowed_values.items():
        if payload[field] not in allowed:
            raise MoomooConfigurationError(
                f"invalid Moomoo paper-account preflight report field: {field}"
            )
    count_fields = {
        "readiness_schema_version",
        "eligible_account_count",
        "position_count",
        "order_record_count",
    }
    if any(
        type(payload[field]) is not int or payload[field] < 0
        for field in count_fields
    ):
        raise MoomooConfigurationError(
            "invalid Moomoo paper-account preflight report payload"
        )
    if type(payload["refresh_cache"]) is not bool:
        raise MoomooConfigurationError(
            "invalid Moomoo paper-account preflight report payload"
        )
    if payload["sanitized_failure_category"] not in {
        None,
        "readiness",
        "version",
        "connection",
        "account",
        "funds",
        "positions",
        "orders",
        "system",
    }:
        raise MoomooConfigurationError(
            "invalid Moomoo paper-account preflight report payload"
        )


def _validate_report_payload(payload: Mapping[str, object]) -> None:
    string_fields = {
        "endpoint",
        "sdk_version",
        "server_version",
        "quote_connection_status",
        "trade_connection_status",
        "us_quote_entitlement",
        "jp_quote_entitlement",
    }
    if any(not isinstance(payload[field], str) for field in string_fields):
        raise MoomooConfigurationError("invalid Moomoo discovery report payload")
    if not _safe_report_endpoint(payload["endpoint"]):
        raise MoomooConfigurationError("invalid Moomoo discovery report payload")
    if payload["sdk_version"] != "UNKNOWN" and not _VERSION_PATTERN.fullmatch(
        payload["sdk_version"]
    ):
        raise MoomooConfigurationError("invalid Moomoo discovery report payload")
    if payload[
        "server_version"
    ] != "UNKNOWN" and not _SERVER_VERSION_PATTERN.fullmatch(
        payload["server_version"]
    ):
        raise MoomooConfigurationError("invalid Moomoo discovery report payload")
    if (
        payload["us_quote_entitlement"] not in MOOMOO_VALID_ENTITLEMENTS
        or payload["jp_quote_entitlement"] not in MOOMOO_VALID_ENTITLEMENTS
    ):
        raise MoomooConfigurationError("invalid Moomoo discovery report payload")

    if payload["quote_connection_status"] not in {"not-run", "ok"} or payload[
        "trade_connection_status"
    ] not in {"not-run", "ok"}:
        raise MoomooConfigurationError("invalid Moomoo discovery report payload")

    optional_bool_fields = {"qot_logged_in", "trd_logged_in"}
    if any(
        payload[field] is not None and not isinstance(payload[field], bool)
        for field in optional_bool_fields
    ):
        raise MoomooConfigurationError("invalid Moomoo discovery report payload")

    bool_fields = {"paper_account_available", "us_market_authorized"}
    if any(not isinstance(payload[field], bool) for field in bool_fields):
        raise MoomooConfigurationError("invalid Moomoo discovery report payload")

    count_fields = {"account_count", "paper_account_count", "real_account_count"}
    if any(
        not isinstance(payload[field], int)
        or isinstance(payload[field], bool)
        or payload[field] < 0
        for field in count_fields
    ):
        raise MoomooConfigurationError("invalid Moomoo discovery report payload")

    if payload["sanitized_failure_category"] not in {
        None,
        "version",
        "connection",
        "response",
        "system",
    }:
        raise MoomooConfigurationError("invalid Moomoo discovery report payload")


def is_moomoo_us_paper_account_eligible(row: object) -> bool:
    return (
        _enum_name(_field(row, "trd_env")) == "SIMULATE"
        and _enum_name(_field(row, "sim_acc_type")) == "STOCK_AND_OPTION"
        and "US" in _market_names(_field(row, "trdmarket_auth"))
        and _enum_name(_field(row, "acc_status")) == "ACTIVE"
    )


def _safe_report_endpoint(value: str) -> bool:
    if not _ENDPOINT_PATTERN.fullmatch(value):
        return False
    port_text = value.rsplit(":", 1)[-1]
    try:
        port = int(port_text)
    except ValueError:
        return False
    return 1 <= port <= 65535


def _version_at_least(current: str, minimum: str) -> bool:
    try:
        current_parts = tuple(int(part) for part in current.split("."))
        minimum_parts = tuple(int(part) for part in minimum.split("."))
    except (AttributeError, ValueError):
        return False
    return current_parts >= minimum_parts


def _records(payload: object) -> list[object]:
    if hasattr(payload, "to_dict"):
        try:
            records = payload.to_dict("records")
        except (TypeError, ValueError) as exc:
            raise MoomooResponseError("unexpected Moomoo account list shape") from exc
        if isinstance(records, list):
            return records
        raise MoomooResponseError("unexpected Moomoo account list shape")
    if isinstance(payload, list):
        return list(payload)
    if isinstance(payload, tuple):
        return list(payload)
    if isinstance(payload, Iterable) and not isinstance(
        payload, (str, bytes, Mapping)
    ):
        return list(payload)
    raise MoomooResponseError("unexpected Moomoo account list shape")


def _field(row: object, name: str) -> object:
    if isinstance(row, Mapping):
        return row.get(name)
    getter = getattr(row, "get", None)
    if callable(getter):
        return getter(name)
    return getattr(row, name, None)


def _enum_name(value: object) -> str:
    if value is None:
        return "UNKNOWN"
    name = getattr(value, "name", None)
    text = str(name if name is not None else value).strip()
    if "." in text:
        text = text.rsplit(".", 1)[-1]
    return text.upper() or "UNKNOWN"


def _market_names(value: object) -> set[str]:
    if isinstance(value, str):
        parts = value.strip("[]").split(",")
    elif isinstance(value, Iterable) and not isinstance(value, (bytes, Mapping)):
        parts = list(value)
    else:
        parts = []
    return {_enum_name(part) for part in parts}


def _safe_version(value: object) -> str:
    if value is None:
        return "UNKNOWN"
    text = str(value).strip()
    return text if _VERSION_PATTERN.fullmatch(text) else "UNKNOWN"


def _safe_server_version(value: object) -> str:
    if value is None:
        return "UNKNOWN"
    text = str(value).strip()
    return text if _SERVER_VERSION_PATTERN.fullmatch(text) else "UNKNOWN"


def _safe_entitlement(value: object) -> str:
    entitlement = _enum_name(value)
    return entitlement if entitlement in MOOMOO_VALID_ENTITLEMENTS else "UNKNOWN"


def _safe_bool(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _safe_nonnegative_int(value: object) -> int:
    if type(value) is int and value >= 0:
        return value
    return 0


def _safe_close(context: object | None) -> None:
    if context is None:
        return
    try:
        context.close()
    except Exception:
        pass
