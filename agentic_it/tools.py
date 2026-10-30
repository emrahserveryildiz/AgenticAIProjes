from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import ROOT

ASSET_FILE = ROOT / "data" / "asset_inventory.json"
SERVICE_STATUS = {
    "vpn": {"status": "operational", "updated": "2026-10-30 09:00 UTC", "note": "No active incident reported."},
    "email": {"status": "degraded", "updated": "2026-10-30 09:00 UTC", "note": "Intermittent sign-in delays are being monitored."},
    "identity": {"status": "operational", "updated": "2026-10-30 09:00 UTC", "note": "No active incident reported."},
    "endpoint": {"status": "operational", "updated": "2026-10-30 09:00 UTC", "note": "No active incident reported."},
    "internal_app": {"status": "operational", "updated": "2026-10-30 09:00 UTC", "note": "No active incident reported."},
}


def lookup_device(device_id: str = "LAP-1042") -> dict[str, Any]:
    """Read-only demo inventory lookup. It never changes device state."""
    try:
        assets = json.loads(ASSET_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"found": False, "message": "Inventory is unavailable."}
    match = next((item for item in assets if item["device_id"].lower() == device_id.lower()), None)
    return {"found": bool(match), "device": match or {}, "message": "Read-only demo inventory."}


def check_service_status(service: str) -> dict[str, Any]:
    key = service.lower().replace(" ", "_")
    aliases = {"outlook": "email", "mail": "email", "mfa": "identity", "remote_access": "vpn", "app": "internal_app"}
    key = aliases.get(key, key)
    return {"service": key, **SERVICE_STATUS.get(key, {"status": "unknown", "note": "No demo status source for this service."})}


def check_vpn_status() -> dict[str, Any]:
    return check_service_status("vpn")


TOOL_DEFINITIONS = [
    {"type": "function", "function": {"name": "check_vpn_status", "description": "Read the demo VPN service health. Read-only.", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}},
    {"type": "function", "function": {"name": "check_service_status", "description": "Read a demo enterprise service health. Read-only.", "parameters": {"type": "object", "properties": {"service": {"type": "string", "enum": ["vpn", "email", "identity", "endpoint", "internal_app"]}}, "required": ["service"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "lookup_device", "description": "Look up a demo device inventory record. Read-only.", "parameters": {"type": "object", "properties": {"device_id": {"type": "string", "description": "Inventory device identifier; default to LAP-1042 when the user did not provide one."}}, "required": ["device_id"], "additionalProperties": False}}}
]


def execute_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "check_vpn_status":
        return check_vpn_status()
    if name == "check_service_status":
        return check_service_status(str(arguments.get("service", "unknown")))
    if name == "lookup_device":
        return lookup_device(str(arguments.get("device_id", "LAP-1042")))
    return {"error": "Tool is not allowlisted."}


def safe_demo_diagnostics(query: str) -> list[dict[str, Any]]:
    lower = query.lower()
    found: list[dict[str, Any]] = []
    if any(word in lower for word in ("vpn", "vpn'e", "vpn’e", "uzaktan")):
        found.append({"tool": "check_vpn_status", "result": check_vpn_status()})
    if any(word in lower for word in ("outlook", "mail", "email", "e-posta", "posta")):
        found.append({"tool": "check_service_status", "result": check_service_status("email")})
    if any(word in lower for word in ("erişim", "access", "uygulama", "app")):
        found.append({"tool": "check_service_status", "result": check_service_status("internal_app")})
    if any(word in lower for word in ("laptop", "bilgisayar", "cihaz", "device")):
        found.append({"tool": "lookup_device", "result": lookup_device("LAP-1042")})
    return found

