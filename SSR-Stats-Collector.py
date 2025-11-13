#!/usr/bin/env python3
# =============================================================================
#  Script:        mist_gateway_stats.py
#  Description:   Interactive Mist gateway stats tool that loads credentials
#                 from 'Token-Org-URL.txt', lets you select a site (hiding
#                 'main_site' when others exist), shows gateway inventory with
#                 site names, and allows you to pick a device to view detailed
#                 stats (CPU, memory, interfaces, uptime, etc.), with optional
#                 non-interactive JSON output.
#  Author:        Stephen Voto
#  Created:      Nov 13, 2025
#
#  DISCLAIMER:
#  This tool is provided "AS IS" for lab, testing, and operational assistance.
#  It is not an official Juniper/Mist product and carries no warranty or
#  support obligation of any kind.
#
#  You are solely responsible for reviewing, testing, and validating this code
#  before use in any production environment. Use at your own risk. The author
#  assumes no liability for outages, data loss, misconfiguration, or any other
#  impact resulting from the use of this script.
# =============================================================================


"""
mist_gateway_stats.py

Simple CLI tool to pull Mist gateway (SSR) stats from a site using the same
Token-Org-URL.txt approach as V-Tool, with an interactive menu:

Interactive mode:
  - Lets you choose a site (hiding 'main_site' if there are others)
  - Lists gateways at that site
  - Lets you pick ONE gateway
  - Immediately shows its inventory/status and full stats
  - Then returns ALL THE WAY BACK to site selection so you can choose
    another site/gateway pair

Non-interactive mode:
  - --site [--device-id] behaves like a direct stats fetch.

Expected Token-Org-URL.txt formats (any of these work):

1) key=value format (recommended)
   token=YOUR_MIST_API_TOKEN
   org_id=YOUR_ORG_ID
   base_url=https://api.mist.com/api/v1
   # or base_url=https://api.mist.com   (both work)

2) Three lines (in order)
   <token>
   <org_id>
   <base_url>

3) JSON dict
   {
     "token": "YOUR_MIST_API_TOKEN",
     "org_id": "YOUR_ORG_ID",
     "base_url": "https://api.mist.com/api/v1"
   }

This script normalizes base_url so it ALWAYS behaves as:
    https://api.mist.com/api/v1
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import requests
import readline

# ---------------------------------------------------------------------------
# Config: Token-Org-URL file
# ---------------------------------------------------------------------------

TOKEN_ORG_URL_FILE = os.path.join(os.path.dirname(__file__), "Token-Org-URL.txt")


# ---------------------------------------------------------------------------
# Helpers to load token/org/base_url
# ---------------------------------------------------------------------------

def normalize_base_url(raw_base_url: str) -> str:
    """
    Normalize base_url so it ALWAYS ends with /api/v1

    Examples:
      'https://api.mist.com'           -> 'https://api.mist.com/api/v1'
      'https://api.mist.com/'         -> 'https://api.mist.com/api/v1'
      'https://api.mist.com/api/v1'   -> 'https://api.mist.com/api/v1'
      'api.mist.com'                  -> 'https://api.mist.com/api/v1'
    """
    b = (raw_base_url or "").strip()
    if not b:
        return ""
    if not b.startswith("http://") and not b.startswith("https://"):
        b = "https://" + b
    b = b.rstrip("/")
    if b.endswith("/api/v1"):
        return b
    return b + "/api/v1"


def load_token_org_url() -> Tuple[str, Optional[str], str]:
    """
    Load Mist API token, org_id, and base_url from Token-Org-URL.txt.

    Supported formats:

    1) key=value lines:
       token=...
       org_id=...
       base_url=...

    2) Three plain lines (token, org_id, base_url)

    3) JSON dict: {"token": "...", "org_id": "...", "base_url": "..."}

    Returns:
        (token, org_id, base_url) where base_url always ends with /api/v1

    Exits with error if token or base_url cannot be determined.
    """
    if not os.path.exists(TOKEN_ORG_URL_FILE):
        print(
            "ERROR: Token-Org-URL.txt not found.\n"
            f"Expected at: {TOKEN_ORG_URL_FILE}\n"
        )
        sys.exit(1)

    with open(TOKEN_ORG_URL_FILE, "r", encoding="utf-8") as f:
        raw = f.read().strip()

    if not raw:
        print(f"ERROR: {TOKEN_ORG_URL_FILE} is empty.")
        sys.exit(1)

    token: Optional[str] = None
    org_id: Optional[str] = None
    base_url: Optional[str] = None

    # First, try JSON
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            token = data.get("token") or data.get("api_token") or data.get("MIST_TOKEN")
            org_id = data.get("org_id") or data.get("ORG_ID")
            base_url = data.get("base_url") or data.get("BASE_URL")
    except Exception:
        data = None

    if token and base_url:
        return token.strip(), (org_id.strip() if org_id else None), normalize_base_url(base_url)

    # Not JSON, parse as lines
    lines = [
        line.strip()
        for line in raw.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    # Try key=value format
    kv: Dict[str, str] = {}
    for line in lines:
        if "=" in line:
            k, v = line.split("=", 1)
            kv[k.strip().lower()] = v.strip()

    if kv:
        token = kv.get("token") or kv.get("mist_token") or kv.get("api_token")
        org_id = kv.get("org_id")
        base_url = kv.get("base_url")
        if token and base_url:
            return token.strip(), (org_id.strip() if org_id else None), normalize_base_url(base_url)

    # Fallback: 3-line positional format
    if len(lines) >= 3:
        token = lines[0]
        org_id = lines[1]
        base_url = lines[2]
        if token and base_url:
            return token.strip(), (org_id.strip() if org_id else None), normalize_base_url(base_url)

    print(
        f"ERROR: Could not parse token/org/base_url from {TOKEN_ORG_URL_FILE}.\n"
        "Supported formats:\n"
        "  1) key=value lines: token=..., org_id=..., base_url=...\n"
        "  2) three lines: <token>, <org_id>, <base_url>\n"
        "  3) JSON dict with token/org_id/base_url\n"
    )
    sys.exit(1)


def make_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Token {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def api_get(url: str, headers: Dict[str, str],
            params: Optional[Dict[str, Any]] = None) -> Any:
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
    except requests.RequestException as e:
        print(f"ERROR: Request failed: {e}")
        sys.exit(1)

    if not resp.ok:
        print(f"ERROR: Mist API returned {resp.status_code}")
        try:
            print(resp.json())
        except Exception:
            print(resp.text)
        sys.exit(1)

    try:
        return resp.json()
    except Exception as e:
        print(f"ERROR: Failed to decode JSON response: {e}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Core Mist calls
# ---------------------------------------------------------------------------

def get_sites(org_id: str, token: str, base_url: str) -> List[Dict[str, Any]]:
    """
    Get list of sites for an org.

    GET /api/v1/orgs/{org_id}/sites
    """
    url = f"{base_url.rstrip('/')}/orgs/{org_id}/sites"
    params = {"limit": 1000}
    headers = make_headers(token)
    data = api_get(url, headers=headers, params=params)

    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and "results" in data:
        return data.get("results", [])
    else:
        print("WARNING: Unexpected response format for sites, dumping raw JSON:")
        print(json.dumps(data, indent=2))
        sys.exit(1)


def get_gateways_for_site(site_id: str,
                          token: str,
                          base_url: str,
                          limit: int = 1000) -> List[Dict[str, Any]]:
    """
    Get inventory devices of type gateway for a site.

    GET /api/v1/sites/{site_id}/devices?type=gateway
    """
    url = f"{base_url.rstrip('/')}/sites/{site_id}/devices"
    params = {
        "type": "gateway",
        "limit": limit,
    }
    headers = make_headers(token)
    data = api_get(url, headers=headers, params=params)

    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and "results" in data:
        return data.get("results", [])
    else:
        print("WARNING: Unexpected response format for devices, dumping raw JSON:")
        print(json.dumps(data, indent=2))
        sys.exit(1)


def get_all_gateway_stats(site_id: str,
                          token: str,
                          base_url: str,
                          limit: int = 1000) -> List[Dict[str, Any]]:
    """
    Call:
      GET /api/v1/sites/{site_id}/stats/devices?type=gateway
    """
    url = f"{base_url.rstrip('/')}/sites/{site_id}/stats/devices"
    params = {
        "type": "gateway",
        "limit": limit,
    }
    headers = make_headers(token)
    data = api_get(url, headers=headers, params=params)

    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and "results" in data:
        # Just in case Mist returns a wrapped format
        return data.get("results", [])
    else:
        print("WARNING: Unexpected response format for stats, dumping raw JSON:")
        print(json.dumps(data, indent=2))
        sys.exit(1)


def get_gateway_stats_for_device(site_id: str,
                                 device_id: str,
                                 token: str,
                                 base_url: str) -> Dict[str, Any]:
    """
    Call:
      GET /api/v1/sites/{site_id}/stats/devices/{device_id}?type=gateway
    """
    url = f"{base_url.rstrip('/')}/sites/{site_id}/stats/devices/{device_id}"
    params = {"type": "gateway"}
    headers = make_headers(token)
    data = api_get(url, headers=headers, params=params)

    if isinstance(data, dict):
        return data
    else:
        print("WARNING: Unexpected response format for single device stats:")
        print(json.dumps(data, indent=2))
        sys.exit(1)


# ---------------------------------------------------------------------------
# Pretty printing
# ---------------------------------------------------------------------------

def print_device_summary(dev: Dict[str, Any]) -> None:
    name = dev.get("name") or dev.get("router_name") or dev.get("_id", "unknown")
    dev_id = dev.get("id", dev.get("_id", ""))
    model = dev.get("model", dev.get("hardware_model", ""))
    version = dev.get("version", "")
    status = dev.get("status", "")
    ip = dev.get("ip", "")
    ext_ip = dev.get("ext_ip", "")
    uptime = dev.get("uptime", 0)

    cpu = dev.get("cpu_stat", {})
    mem = dev.get("memory_stat", {})
    load_avg = cpu.get("load_avg", [])
    load_str = ", ".join(str(x) for x in load_avg) if load_avg else "n/a"
    mem_usage = mem.get("usage", "n/a")

    print("=" * 80)
    print(f"Device: {name}")
    if dev_id:
        print(f"  ID: {dev_id}")
    if model:
        print(f"  Model: {model}")
    if version:
        print(f"  Version: {version}")
    print(f"  Status: {status}")
    print(f"  IP: {ip}")
    print(f"  Ext IP: {ext_ip}")
    print(f"  Uptime (s): {uptime}")
    print(f"  CPU load avg: {load_str}")
    print(f"  Memory usage: {mem_usage}%")

    if_stat = dev.get("if_stat", {})
    if if_stat:
        print("  Interfaces:")
        for if_name, if_info in sorted(if_stat.items()):
            port_usage = if_info.get("port_usage", "")
            network_name = if_info.get("network_name", "")
            ips = if_info.get("ips", [])
            up = if_info.get("up", False)
            rx_pkts = if_info.get("rx_pkts", 0)
            tx_pkts = if_info.get("tx_pkts", 0)
            print(f"    - {if_name}:")
            print(f"        usage: {port_usage}")
            if network_name:
                print(f"        network: {network_name}")
            if ips:
                print(f"        ips: {', '.join(ips)}")
            print(f"        up: {up}")
            print(f"        rx_pkts: {rx_pkts}, tx_pkts: {tx_pkts}")


def print_all_devices_summary(devices: List[Dict[str, Any]]) -> None:
    if not devices:
        print("No gateway devices found for this site.")
        return

    print(f"Found {len(devices)} gateway device(s):")
    print()
    for dev in devices:
        print_device_summary(dev)


# ---------------------------------------------------------------------------
# Interactive menus
# ---------------------------------------------------------------------------

def choose_from_list(prompt: str, items: List[str]) -> Optional[int]:
    """
    Generic helper to choose a single index from a list of strings.

    Returns 0-based index, or None if user quits.
    """
    if not items:
        print("No items to choose from.")
        return None

    print()
    print(prompt)
    for idx, text in enumerate(items, start=1):
        print(f"  {idx}. {text}")
    print("  q. Quit")
    while True:
        choice = input("Enter choice: ").strip().lower()
        if choice in ("q", "quit", "x", "exit"):
            return None
        if not choice.isdigit():
            print("Please enter a valid number or 'q' to quit.")
            continue
        idx = int(choice)
        if 1 <= idx <= len(items):
            return idx - 1
        print(f"Please enter a number between 1 and {len(items)}, or 'q' to quit.")


def interactive_stats_workflow(token: str,
                               org_id: Optional[str],
                               base_url: str,
                               json_output: bool = False,
                               limit: int = 1000) -> None:
    """
    Interactive flow:

    OUTER LOOP:
      - Choose site
      - Choose gateway on that site
      - Show inventory + stats
      - Then go back to site selection

    Behavior details:
      - Hides 'main_site' from site list if there are other sites.
      - 'q' at site list exits script.
      - 'q' at gateway list returns to site list.
    """
    while True:
        # Step 1: choose site
        if org_id:
            try:
                sites_all = get_sites(org_id, token, base_url)
            except SystemExit:
                return
            if not sites_all:
                print(f"No sites found for org {org_id}.")
                return

            # Filter out main_site by name (case-insensitive), but only if there are others
            filtered_sites = [
                s for s in sites_all
                if s.get("name", "").lower() != "main_site"
            ]
            sites = filtered_sites if filtered_sites else sites_all

            site_labels = []
            for s in sites:
                name = s.get("name", "unnamed-site")
                site_id = s.get("id", "")
                site_labels.append(f"{name} ({site_id})")

            idx = choose_from_list("Select a site:", site_labels)
            if idx is None:
                print("Exiting gateway stats viewer.")
                return

            site_id = sites[idx].get("id")
            if not site_id:
                print("ERROR: Selected site has no 'id'. Aborting.")
                return
        else:
            print("org_id not found in Token-Org-URL.txt.")
            site_id = input("Enter site_id to query gateway stats (or 'q' to quit): ").strip()
            if not site_id or site_id.lower() in ("q", "quit", "x", "exit"):
                print("Exiting gateway stats viewer.")
                return

        print()
        print(f"Selected site_id: {site_id}")
        print("Fetching gateway inventory...")

        gateways = get_gateways_for_site(site_id, token, base_url, limit=limit)
        if not gateways:
            print("No gateway devices found for this site.")
            # Go back to site selection
            continue

        print()
        print(f"Found {len(gateways)} gateway device(s):")
        gateway_labels: List[str] = []
        for idx, gw in enumerate(gateways, start=1):
            name = gw.get("name") or gw.get("router_name") or "unnamed"
            mac = gw.get("mac", "")
            device_id = gw.get("id", "")
            model = gw.get("model", "")
            status = gw.get("status", "")
            label = f"[{idx}] {name}  MAC:{mac}  ID:{device_id}  Model:{model}  Status:{status}"
            print(label)
            gateway_labels.append(label)

        # Pre-fetch stats for this site
        all_stats = get_all_gateway_stats(site_id, token, base_url, limit=limit)
        stats_by_key: Dict[str, Dict[str, Any]] = {}
        for st in all_stats:
            key = st.get("id") or st.get("_id") or st.get("mac")
            if key:
                stats_by_key[str(key)] = st

        print()
        print("Select a gateway to view stats (or 'q' to go back to site selection).")

        gw_idx = choose_from_list(
            "Gateway selection:",
            gateway_labels,
        )
        if gw_idx is None:
            # Back to site selection (outer loop)
            continue

        gw = gateways[gw_idx]
        name = gw.get("name") or gw.get("router_name") or "unnamed"
        mac = gw.get("mac", "")
        dev_id = gw.get("id", "")
        model = gw.get("model", "")
        status = gw.get("status", "")

        # Immediately show selected gateway basic status from inventory
        print()
        print("-" * 80)
        print("Selected gateway (inventory):")
        print(f"  Name:   {name}")
        print(f"  MAC:    {mac}")
        print(f"  ID:     {dev_id}")
        print(f"  Model:  {model}")
        print(f"  Status: {status}")
        print("-" * 80)

        inv_key = dev_id or mac or gw.get("_id")
        stats: Optional[Dict[str, Any]] = None

        if inv_key is not None:
            stats = stats_by_key.get(str(inv_key))

        # Fallback: try MAC directly if not found by ID
        if stats is None and mac:
            stats = stats_by_key.get(mac)

        if stats is None:
            print("No stats found for selected gateway.")
        else:
            print()
            if json_output:
                print(json.dumps(stats, indent=2, sort_keys=True))
            else:
                print_device_summary(stats)

        print()
        input("Press Enter to return to site selection...")
        # loop continues, back to site selection


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Get Mist gateway (SSR) stats using Token-Org-URL.txt.\n"
            "If --site is not provided, an interactive menu is used to pick "
            "a site and a gateway. After showing stats, you return to the "
            "site selection menu."
        )
    )
    parser.add_argument(
        "--site", "-s",
        help="Mist site_id (e.g. a618679d-e590-48c7-a6bd-b3f3c5630f5b). "
             "If omitted, interactive site selection is used.",
    )
    parser.add_argument(
        "--device-id", "-d",
        help="Optional device_id to fetch only that device's stats (non-interactive).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of pretty summary.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Maximum number of devices/stats to fetch (default: 1000).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    token, org_id, base_url = load_token_org_url()

    # Just informational; not required for stats
    if org_id:
        print(f"Using org_id from Token-Org-URL.txt: {org_id}")
    print(f"Using base_url: {base_url}")
    print()

    # Non-interactive mode
    if args.site:
        site_id = args.site
        if args.device_id:
            # Single device stats
            dev_stats = get_gateway_stats_for_device(site_id, args.device_id, token, base_url)
            if args.json:
                print(json.dumps(dev_stats, indent=2, sort_keys=True))
            else:
                print_device_summary(dev_stats)
        else:
            # All gateway stats for the site
            devices_stats = get_all_gateway_stats(site_id, token, base_url, limit=args.limit)
            if args.json:
                print(json.dumps(devices_stats, indent=2, sort_keys=True))
            else:
                print_all_devices_summary(devices_stats)
        return

    # Interactive mode
    interactive_stats_workflow(
        token=token,
        org_id=org_id,
        base_url=base_url,
        json_output=args.json,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()

