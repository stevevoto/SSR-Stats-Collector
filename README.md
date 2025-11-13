# SSR-Stats-Collector
Interactive Mist SSR gateway stats tool that reads Token-Org-URL.txt, lets you pick a site and gateway, then shows detailed stats (status, uptime, CPU, memory, interfaces, IPs). Supports JSON output and non-interactive mode using site and device IDs.

# SSR Stats Tool (Mist Gateway Stats)

## Overview

Interactive Mist SSR gateway stats tool that reads `Token-Org-URL.txt`, lets you pick a site and gateway, then shows detailed stats (status, uptime, CPU, memory, interfaces, IPs). Supports JSON output and non-interactive mode using site and device IDs.

- **Script:** `SSR-Stats-Collector.py`  
- **Author:** Stephen Voto  

---

## Token-Org-URL.txt Format

The script expects a file named `Token-Org-URL.txt` in the same directory, with at least these fields:

```text
token=YOUR_MIST_API_TOKEN
org_id=YOUR_ORG_ID
base_url=https://api.mist.com/api/v1
base_url can be either:

https://api.mist.com

https://api.mist.com/api/v1

The script normalizes it so it always uses the /api/v1 form.

Note: The script also supports 3-line positional and JSON formats internally, but the key/value format above is recommended.

Requirements
Python 3.7+

requests library

Install dependencies:

bash
Copy code
pip install requests
Usage
Interactive Mode (Site & Gateway Selection)
From the directory containing the script and Token-Org-URL.txt:

bash
Copy code
python3 SSR-Stats-Collector.py
The script will:

Load credentials and normalize base_url.

Fetch the list of sites for your org.

Show a site selection menu (hides main_site when other sites exist).

After you pick a site, it shows a list of gateway devices on that site.

You select a gateway and the script prints a detailed stats summary.

Use q at any selection prompt to exit.

Non-Interactive Mode
If you already know the site_id and/or device_id, you can run it directly:

All Gateway Stats for a Site (Summary)
bash
Copy code
python3 SSR-Stats-Collector.py --site a618679d-e590-48c7-a6bd-b3f3c5630f5b
All Gateway Stats for a Site (Raw JSON)
bash
Copy code
python3 SSR-Stats-Collector.py --site a618679d-e590-48c7-a6bd-b3f3c5630f5b --json
Single Device Stats (Summary)
bash
Copy code
python3 SSR-Stats-Collector.py \
  --site a618679d-e590-48c7-a6bd-b3f3c5630f5b \
  --device-id 00000000-0000-0000-1000-02000117f2d8
Single Device Stats (Raw JSON)
bash
Copy code
python3 SSR-Stats-Collector.py \
  --site a618679d-e590-48c7-a6bd-b3f3c5630f5b \
  --device-id 00000000-0000-0000-1000-02000117f2d8 \
  --json
Example Interactive Flow
Run:

bash
Copy code
python3 SSR-Stats-Collector.py
Site selection appears, for example:

text
Copy code
Select a site:
  1. Seattle (a618679d-e590-48c7-a6bd-b3f3c5630f5b)
  2. Boston  (b7123abc-1234-4567-89ab-0123456789ab)
  q. Quit
After selecting a site, gateway inventory is shown:

text
Copy code
Found 2 gateway device(s):
[1] seattle-ssr-1  MAC:02000117f2d8  ID:00000000-0000-0000-1000-02000117f2d8  Model:SSR  Status:connected
[2] seattle-ssr-2  MAC:02000117f3aa  ID:00000000-0000-0000-1000-02000117f3aa  Model:SSR  Status:connected
You pick a gateway by number. The script:

Echoes the selected device info (name, MAC, model, status).

Prints a detailed stats summary including:

Status, version, uptime

CPU load averages

Memory usage

Interface stats (LAN/WAN, IPs, packets, up/down)

Depending on the script flow you’re using, it will then either:

Ask if you want to view another device’s stats, or

Return to site selection so you can pick a different site and gateway.

To quit at any point, enter q at the prompt.

Notes & Behavior
Stats are pulled from Mist via:

GET /api/v1/sites/{site_id}/stats/devices?type=gateway

GET /api/v1/sites/{site_id}/stats/devices/{device_id}?type=gateway

Site information is pulled from:

GET /api/v1/orgs/{org_id}/sites

The script matches stats to devices using:

id or _id where possible, or

MAC address as a fallback.

main_site is hidden from the site list when there are other sites, to reduce clutter.

Disclaimer
This tool is provided "AS IS" for lab, testing, and operational assistance.
It is not an official Juniper/Mist product and carries no warranty or support obligation.

You are solely responsible for reviewing, testing, and validating this code before use in any environment. Use at your own risk. The author assumes no liability for outages, data loss, misconfiguration, or any other impact resulting from the use of this script.

perl
Copy code
