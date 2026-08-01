from __future__ import annotations

import importlib
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Protocol


MIN_MOOMOO_API_VERSION = "10.4.6408"
MOOMOO_DISCOVERY_SCHEMA_VERSION = 1
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
_VERSION_PATTERN = re.compile(r"\d+(?:\.\d+){2,3}")
_SERVER_VERSION_PATTERN = re.compile(r"\d+(?:\.\d+){0,3}")
_ENDPOINT_PATTERN = re.compile(r"(?:127\.0\.0\.1|localhost):\d{1,5}|\[::1\]:\d{1,5}")
_ENTITLEMENTS = frozenset({"NO", "BMP", "LV1", "LV2", "LV3", "SF", "UNKNOWN"})


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

    def close(self) -> None: ...


class MoomooSdkSource(Protocol):
    version: str
    ret_ok: int

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
        output_path = Path(path)
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("x", encoding="utf-8") as stream:
                json.dump(result.to_dict(), stream, sort_keys=True)
                stream.write("\n")
        except FileExistsError as exc:
            raise MoomooConfigurationError(
                "Moomoo discovery report already exists"
            ) from exc
        except OSError as exc:
            raise MoomooConfigurationError(
                "could not write the Moomoo discovery report"
            ) from exc
        return output_path


class MoomooDiscoveryReportReader:
    def read(self, path: str | Path) -> MoomooDiscoveryResult:
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
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
        payload["us_quote_entitlement"] not in _ENTITLEMENTS
        or payload["jp_quote_entitlement"] not in _ENTITLEMENTS
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
    return entitlement if entitlement in _ENTITLEMENTS else "UNKNOWN"


def _safe_bool(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _safe_close(context: object | None) -> None:
    if context is None:
        return
    try:
        context.close()
    except Exception:
        pass
