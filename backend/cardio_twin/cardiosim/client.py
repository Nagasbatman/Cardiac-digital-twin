"""CardioSim HTTP integration client.

All network communication with the CardioSim backend is concentrated here.
The module raises explicit, typed exceptions for every failure mode — callers
must never receive a success-shaped fallback when the real request failed.

Usage example::

    from cardiosim.client import CardioSimClient

    client = CardioSimClient()          # uses BASE_URL from config
    presets = client.get_presets()      # dict[str, PresetInfo]
    response = client.simulate(
        preset="Healthy Adult",
        hr=75,
        contract=100,
        resist=1.0,
        compl=1.46,
        duration=6.0,
    )
    print(response.primary.metrics.co)  # cardiac output
"""
from __future__ import annotations

from typing import Any

import requests

from cardiosim import config
from cardiosim.models import PresetInfo, SimResponse, SimResult

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class CardioSimError(Exception):
    """Base class for all CardioSim client errors."""


class CardioSimConnectionError(CardioSimError):
    """Raised when the backend cannot be reached (refused, DNS, network)."""


class CardioSimTimeoutError(CardioSimError):
    """Raised when the request exceeds the configured timeout."""


class CardioSimHTTPError(CardioSimError):
    """Raised for non-2xx HTTP responses.

    Attributes:
        status_code: The HTTP status code returned by the server.
        detail: Text body of the error response, if available.
    """

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")


class CardioSimResponseError(CardioSimError):
    """Raised when the response body is not valid JSON or has an unexpected shape."""


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

_PRESET_REQUIRED_FIELDS = {"hr", "contract", "resist", "compl", "desc", "category"}
_SIM_RESULT_REQUIRED_FIELDS = {"t", "X", "ecg", "preset", "params", "metrics", "rr"}
_METRICS_SCALAR_FIELDS = {"co", "sv", "sys", "dia", "map_val", "pp", "ef", "hr"}
_METRICS_ARRAY_FIELDS = {"lv_vol", "lvp", "lvof", "lvp_full"}


def _validate_preset_entry(name: str, entry: Any) -> None:
    """Raise CardioSimResponseError if *entry* is not a valid preset object."""
    if not isinstance(entry, dict):
        raise CardioSimResponseError(
            f"Preset {name!r}: expected a dict, got {type(entry).__name__}"
        )
    missing = _PRESET_REQUIRED_FIELDS - entry.keys()
    if missing:
        raise CardioSimResponseError(
            f"Preset {name!r}: missing fields {sorted(missing)}"
        )
    for field in ("hr", "contract", "resist", "compl"):
        if not isinstance(entry[field], (int, float)):
            raise CardioSimResponseError(
                f"Preset {name!r}: field {field!r} must be numeric, "
                f"got {type(entry[field]).__name__}"
            )


def _validate_metrics(metrics: Any, context: str) -> None:
    """Raise CardioSimResponseError if *metrics* does not match the expected shape."""
    if not isinstance(metrics, dict):
        raise CardioSimResponseError(
            f"{context} metrics: expected a dict, got {type(metrics).__name__}"
        )
    missing = (_METRICS_SCALAR_FIELDS | _METRICS_ARRAY_FIELDS) - metrics.keys()
    if missing:
        raise CardioSimResponseError(
            f"{context} metrics: missing fields {sorted(missing)}"
        )
    for field in _METRICS_SCALAR_FIELDS:
        if not isinstance(metrics[field], (int, float)):
            raise CardioSimResponseError(
                f"{context} metrics.{field}: expected a number, "
                f"got {type(metrics[field]).__name__}"
            )
    for field in _METRICS_ARRAY_FIELDS:
        if not isinstance(metrics[field], list):
            raise CardioSimResponseError(
                f"{context} metrics.{field}: expected a list, "
                f"got {type(metrics[field]).__name__}"
            )


def _validate_sim_result(result: Any, context: str) -> None:
    """Raise CardioSimResponseError if *result* does not match SimResult shape."""
    if not isinstance(result, dict):
        raise CardioSimResponseError(
            f"{context}: expected a dict, got {type(result).__name__}"
        )
    missing = _SIM_RESULT_REQUIRED_FIELDS - result.keys()
    if missing:
        raise CardioSimResponseError(
            f"{context}: missing top-level fields {sorted(missing)}"
        )
    for field in ("t", "X", "ecg"):
        if not isinstance(result[field], list):
            raise CardioSimResponseError(
                f"{context}.{field}: expected a list, got {type(result[field]).__name__}"
            )
    if not isinstance(result["preset"], str):
        raise CardioSimResponseError(
            f"{context}.preset: expected a str, got {type(result['preset']).__name__}"
        )
    if not isinstance(result["params"], dict):
        raise CardioSimResponseError(
            f"{context}.params: expected a dict, got {type(result['params']).__name__}"
        )
    # rr may be a list or null
    if result["rr"] is not None and not isinstance(result["rr"], list):
        raise CardioSimResponseError(
            f"{context}.rr: expected a list or null, got {type(result['rr']).__name__}"
        )
    _validate_metrics(result.get("metrics"), context)


def _validate_simulate_response(body: Any) -> None:
    """Raise CardioSimResponseError if the /api/simulate response is malformed."""
    if not isinstance(body, dict):
        raise CardioSimResponseError(
            f"/api/simulate: expected a JSON object, got {type(body).__name__}"
        )
    if "primary" not in body:
        raise CardioSimResponseError(
            "/api/simulate: response missing required 'primary' field"
        )
    if body["primary"] is None:
        raise CardioSimResponseError(
            "/api/simulate: 'primary' result is null — simulation did not converge"
        )
    _validate_sim_result(body["primary"], "primary")
    # 'comparison' must be present; it is either a result object or null
    if "comparison" not in body:
        raise CardioSimResponseError(
            "/api/simulate: response missing required 'comparison' field"
        )
    if body["comparison"] is not None:
        _validate_sim_result(body["comparison"], "comparison")


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class CardioSimClient:
    """Thin HTTP wrapper for the CardioSim backend.

    Parameters:
        base_url: Override the backend URL (defaults to ``config.BASE_URL``).
        connect_timeout: TCP connection timeout in seconds.
        read_timeout: Response read timeout in seconds.
    """

    def __init__(
        self,
        base_url: str | None = None,
        connect_timeout: float = config.CONNECT_TIMEOUT,
        read_timeout: float = config.READ_TIMEOUT,
    ) -> None:
        self._base_url = (base_url or config.BASE_URL).rstrip("/")
        self._timeout = (connect_timeout, read_timeout)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(self, path: str) -> Any:
        url = f"{self._base_url}{path}"
        try:
            resp = requests.get(url, timeout=self._timeout)
        except requests.exceptions.ConnectionError as exc:
            raise CardioSimConnectionError(
                f"Cannot connect to CardioSim at {url}: {exc}"
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise CardioSimTimeoutError(
                f"Request to {url} timed out: {exc}"
            ) from exc
        if not resp.ok:
            raise CardioSimHTTPError(resp.status_code, resp.text[:500])
        try:
            return resp.json()
        except Exception as exc:
            raise CardioSimResponseError(
                f"GET {url}: response is not valid JSON — {exc}"
            ) from exc

    def _post(self, path: str, payload: dict[str, Any]) -> Any:
        url = f"{self._base_url}{path}"
        try:
            resp = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self._timeout,
            )
        except requests.exceptions.ConnectionError as exc:
            raise CardioSimConnectionError(
                f"Cannot connect to CardioSim at {url}: {exc}"
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise CardioSimTimeoutError(
                f"Request to {url} timed out: {exc}"
            ) from exc
        if not resp.ok:
            raise CardioSimHTTPError(resp.status_code, resp.text[:500])
        try:
            return resp.json()
        except Exception as exc:
            raise CardioSimResponseError(
                f"POST {url}: response is not valid JSON — {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_presets(self) -> dict[str, PresetInfo]:
        """Retrieve and validate all available simulation presets.

        Returns:
            A dict mapping preset name → :class:`PresetInfo`.

        Raises:
            CardioSimConnectionError: Backend is unreachable.
            CardioSimTimeoutError: Request timed out.
            CardioSimHTTPError: Non-2xx response.
            CardioSimResponseError: Response is not valid JSON or has wrong shape.
        """
        body = self._get("/api/presets")
        if not isinstance(body, dict):
            raise CardioSimResponseError(
                f"GET /api/presets: expected a JSON object, got {type(body).__name__}"
            )
        if not body:
            raise CardioSimResponseError(
                "GET /api/presets: response object is empty — no presets returned"
            )
        presets: dict[str, PresetInfo] = {}
        for name, entry in body.items():
            _validate_preset_entry(name, entry)
            presets[name] = PresetInfo.from_api(name, entry)
        return presets

    def simulate(
        self,
        *,
        preset: str,
        hr: float,
        contract: float,
        resist: float,
        compl: float,
        duration: float,
        compare_preset: str | None = None,
    ) -> SimResponse:
        """Submit a simulation request and return the validated response.

        All six required parameters must be supplied explicitly by the caller.
        ``compare_preset`` is optional; omit it to get only a ``primary`` result.

        Parameters:
            preset: Name of the clinical preset (must exist in ``get_presets()``).
            hr: Heart rate (bpm).
            contract: Contractility (%).
            resist: Peripheral resistance (mmHg·s/mL).
            compl: Arterial compliance (mL/mmHg).
            duration: Simulation duration (seconds).
            compare_preset: Optional second preset for side-by-side comparison.

        Returns:
            :class:`SimResponse` with ``primary`` always set and ``comparison``
            set only when ``compare_preset`` was provided and valid.

        Raises:
            CardioSimConnectionError: Backend is unreachable.
            CardioSimTimeoutError: Request timed out.
            CardioSimHTTPError: Non-2xx response (e.g. 400 for unknown preset).
            CardioSimResponseError: Response is not valid JSON or has wrong shape.
        """
        payload: dict[str, Any] = {
            "preset": preset,
            "hr": hr,
            "contract": contract,
            "resist": resist,
            "compl": compl,
            "duration": duration,
        }
        if compare_preset is not None:
            payload["compare_preset"] = compare_preset

        body = self._post("/api/simulate", payload)
        _validate_simulate_response(body)
        return SimResponse(
            primary=SimResult.from_api(body["primary"]),
            comparison=SimResult.from_api(body["comparison"])
            if body["comparison"] is not None
            else None,
        )

