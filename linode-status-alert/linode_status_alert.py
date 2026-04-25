import requests
import time
import os
import schedule
from datetime import datetime, timedelta, timezone

# ================= Configuration Area =================
# 1. Feishu/Lark Webhook URL
FEISHU_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/b21647e5-e09c-4cea-956e-6629997d9d45"

# 2. Keyword filtering (Must match the keyword configured in the Feishu bot security settings)
KEYWORD = "Linode" 

# ================= Incident Configuration =================
# Check interval for unresolved incidents (in seconds)
INCIDENT_CHECK_INTERVAL = 300

# Minimum impact level threshold: 'none', 'minor', 'major', 'critical'
MIN_IMPACT_LEVEL = "minor" 

# State record file for deduplication
STATE_FILE = "linode_monitor_state.txt"

# Exact components to monitor for INCIDENTS.
# Empty list [] means monitoring ALL components without filtering.
# Format: Lowercase exact match. e.g., ["sg-sin-2 (singapore 2)", "linode manager and api"]
INCIDENT_COMPONENTS = []

# ================= Maintenance Configuration =================
# Schedule Toggles
ENABLE_DAILY_MAINTENANCE = True   # Enable daily reminders
ENABLE_WEEKLY_MAINTENANCE = True  # Enable weekly overview

# Scheduled Execution Times (Server Local Time)
# IMPORTANT: Since the schedule library relies on the server's local time, 
# please ensure these times align with your server's timezone.
DAILY_EXECUTION_TIME_LOCAL = "09:01"
WEEKLY_EXECUTION_TIME_LOCAL = "09:00"

# Exact components to monitor for SCHEDULED MAINTENANCES.
# Empty list [] means monitoring ALL components without filtering.
# Format: Lowercase exact match.
MAINTENANCE_COMPONENTS = []

# ====================================================

IMPACT_WEIGHTS = {"none": 0, "minor": 1, "major": 2, "critical": 3}

def get_current_utc_str():
    """Helper to get formatted UTC time string for logging."""
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

def is_component_relevant(components, interested_list):
    """
    Check if the incident/maintenance components match the interested list.
    If the interested list is empty, return True (monitor all).
    """
    if not interested_list:
        return True
    
    for comp in components:
        name = comp.get('name', '').strip().lower()
        if name in interested_list:
            return True
    return False

# ================= Feishu Notification Functions =================

def send_incident_to_feishu(title, content, impact_level):
    """Send a rich text message to Feishu for Incidents."""
    tag = "🔴" if IMPACT_WEIGHTS.get(impact_level, 0) >= 2 else "⚠️"
    
    payload = {
        "msg_type": "post",
        "content": {
            "post": {
                "en_us": {  
                    "title": f"{tag} {title} ({impact_level.upper()})",
                    "content": [
                        [{"tag": "text", "text": f"{content}\n\nKeyword: {KEYWORD}"}],
                        [{"tag": "a", "text": "View Official Status Page", "href": "https://status.linode.com"}]
                    ]
                }
            }
        }
    }
    
    try:
        requests.post(FEISHU_URL, json=payload, timeout=10)
    except Exception as e:
        print(f"[{get_current_utc_str()}] Failed to send Feishu incident notification: {e}")

def send_maintenance_to_feishu(title, maintenances, period_desc, force_send=False):
    """Send a batched rich text message to Feishu for Scheduled Maintenances."""
    if not maintenances:
        if not force_send:
            print(f"[{get_current_utc_str()}] {title}: No matching maintenance scheduled. Skipping push.")
            return
        
        # Content to send when forced (usually for weekly reports to prove the bot is alive)
        content_list = [[{"tag": "text", "text": f"✅ No planned maintenance for Linode platform in the upcoming {period_desc}." }]]
    else:
        content_list = []
        for m in maintenances:
            start_time = m.get('scheduled_for', 'Unknown')
            try:
                # API returns ISO 8601, format it explicitly to UTC string
                dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                formatted_time = dt.strftime('%Y-%m-%d %H:%M (UTC)')
            except Exception:
                formatted_time = start_time

            item = [
                {"tag": "text", "text": f"🛠  Maintenance Project: {m.get('name')}\n"},
                {"tag": "text", "text": f"⏰ Scheduled Time: {formatted_time}\n"},
                {"tag": "text", "text": f"⚠️ Impact Level: {m.get('impact', 'unknown').upper()}\n"},
                {"tag": "text", "text": f"📦 Affected Components: {', '.join([c.get('name', 'unknown') for c in m.get('components', [])])}\n"},
                {"tag": "text", "text": "--------------------------------\n"}
            ]
            content_list.extend(item)
            
        content_list = [content_list]

    payload = {
        "msg_type": "post",
        "content": {
            "post": {
                "en_us": {
                    "title": f"🔔 {title} ({period_desc})",
                    "content": [
                        *content_list,
                        [{"tag": "a", "text": "View Official Status Page", "href": "https://status.linode.com"}],
                        [{"tag": "text", "text": f"\nKeyword: {KEYWORD}"}]
                    ]
                }
            }
        }
    }

    try:
        resp = requests.post(FEISHU_URL, json=payload, timeout=10)
        resp.raise_for_status()
        print(f"[{get_current_utc_str()}] Feishu maintenance notification sent: {title}")
    except Exception as e:
        print(f"[{get_current_utc_str()}] Failed to push maintenance to Feishu: {e}")

# ================= Core Logic Functions =================

def check_incidents():
    """Fetch Linode status and process unresolved incidents."""
    api_url = "https://status.linode.com/api/v2/incidents/unresolved.json"
    
    try:
        response = requests.get(api_url, timeout=15)
        response.raise_for_status()
        data = response.json()
        incidents = data.get('incidents', [])

        for incident in incidents:
            impact = incident.get('impact', 'none').lower()
            
            # 1. Filter by impact level
            if IMPACT_WEIGHTS.get(impact, 0) < IMPACT_WEIGHTS.get(MIN_IMPACT_LEVEL, 0):
                continue

            # 2. Filter by exact component relevance
            components = incident.get('components', [])
            if not is_component_relevant(components, INCIDENT_COMPONENTS):
                continue

            # 3. Deduplicate by state (prevent spamming the same incident)
            record_key = f"{incident['id']}_{incident['status']}"
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, 'r') as f:
                    if record_key in f.read(): 
                        continue

            # 4. Execute notification payload
            affected_comps = ", ".join([c['name'] for c in components])
            msg = (f"Incident: {incident['name']}\n"
                   f"Status: {incident['status']}\n"
                   f"Affected Components: {affected_comps}")
            
            send_incident_to_feishu("Linode Platform Alert", msg, impact)

            # Record the state to avoid duplicate alerts
            with open(STATE_FILE, 'a') as f:
                f.write(record_key + "\n")
                
    except Exception as e:
        print(f"[{get_current_utc_str()}] Error checking Linode incident status: {e}")

def fetch_and_filter_maintenances(hours_ahead):
    """Fetch from API and filter upcoming maintenance plans within the specified hours ahead."""
    api_url = "https://status.linode.com/api/v2/scheduled-maintenances/upcoming.json"
    now_utc = datetime.now(timezone.utc)
    limit_utc = now_utc + timedelta(hours=hours_ahead)

    try:
        response = requests.get(api_url, timeout=15)
        response.raise_for_status()
        data = response.json()
        all_maintenances = data.get('scheduled_maintenances', [])

        filtered = []
        for m in all_maintenances:
            sched_str = m.get('scheduled_for')
            if not sched_str: 
                continue

            # 1. Filter by exact component relevance
            components = m.get('components', [])
            if not is_component_relevant(components, MAINTENANCE_COMPONENTS):
                continue

            # 2. Time Validation Logic
            try:
                # Parse ISO 8601 timestamp returned by API
                sched_dt = datetime.fromisoformat(sched_str.replace('Z', '+00:00'))
                
                # Collect if scheduled time is within the target window
                if now_utc <= sched_dt <= limit_utc:
                    filtered.append(m)
            except Exception as e:
                print(f"[{get_current_utc_str()}] Failed to parse time ({sched_str}): {e}")
                continue

        return filtered

    except Exception as e:
        print(f"[{get_current_utc_str()}] Failed to fetch maintenance data: {e}")
        return []

def job_daily_maintenance():
    """Daily check job for maintenances."""
    print(f"[{get_current_utc_str()}] Starting daily maintenance check...")
    maintenances = fetch_and_filter_maintenances(24)
    if maintenances:
        send_maintenance_to_feishu("Linode Daily Maintenance Reminder", maintenances, "24 Hours")

def job_weekly_maintenance():
    """Weekly overview job for maintenances."""
    print(f"[{get_current_utc_str()}] Starting weekly maintenance overview...")
    maintenances = fetch_and_filter_maintenances(7 * 24)
    send_maintenance_to_feishu("Linode Weekly Maintenance Overview", maintenances, "7 Days", force_send=True)

# ================= Main Execution =================

if __name__ == "__main__":
    print(f"[{get_current_utc_str()}] 🚀 Linode Unified Monitor Service Started...")
    
    # Setup Summary
    print("-" * 50)
    print(f"⏰ Incident Check Interval: Every {INCIDENT_CHECK_INTERVAL} seconds")
    print(f"📊 Incident Minimum Alert Level: {MIN_IMPACT_LEVEL.upper()}")
    
    if INCIDENT_COMPONENTS:
        print(f"📍 Incident Exact Components Monitored:\n   " + "\n   ".join(INCIDENT_COMPONENTS))
    else:
        print(f"📍 Incident Exact Components Monitored: [ALL COMPONENTS]")
        
    print("-" * 50)
    
    if ENABLE_DAILY_MAINTENANCE:
        print(f"⏰ Daily Maintenance Check enabled at {DAILY_EXECUTION_TIME_LOCAL} (Server Local Time)")
    if ENABLE_WEEKLY_MAINTENANCE:
        print(f"⏰ Weekly Maintenance Check enabled at {WEEKLY_EXECUTION_TIME_LOCAL} (Server Local Time) on Mondays")

    if MAINTENANCE_COMPONENTS:
        print(f"📍 Maintenance Exact Components Monitored:\n   " + "\n   ".join(MAINTENANCE_COMPONENTS))
    else:
        print(f"📍 Maintenance Exact Components Monitored: [ALL COMPONENTS]")
    print("-" * 50)

    # 1. Execute initial data fetch to build state/cache silently
    print("Executing initial background check...")
    check_incidents()
    
    # 2. Send the startup test notification
    print("Sending startup test notification...")
    try:
        test_maint = fetch_and_filter_maintenances(7 * 24)
        send_maintenance_to_feishu("Linode Monitor Service Started / Restarted", test_maint, "7 Days", force_send=True)
    except Exception as e:
        # Catch errors here to prevent the script from crashing during startup if the network is temporarily unavailable
        print(f"[{get_current_utc_str()}] [WARNING] Failed to send startup notification, but continuing script execution. Error: {e}")
        
    print("Initialization complete.")
    print("-" * 50)

    # 3. Schedule setup
    try:
        schedule.every(INCIDENT_CHECK_INTERVAL).seconds.do(check_incidents)
        
        if ENABLE_DAILY_MAINTENANCE:
            schedule.every().day.at(DAILY_EXECUTION_TIME_LOCAL).do(job_daily_maintenance)
        if ENABLE_WEEKLY_MAINTENANCE:
            schedule.every().monday.at(WEEKLY_EXECUTION_TIME_LOCAL).do(job_weekly_maintenance)
    except Exception as e:
        print(f"[{get_current_utc_str()}] [FATAL ERROR] Failed to setup schedule: {e}")
        raise  # Crash explicitly so systemd can restart it if the schedule setup completely fails

    # 4. Main loop
    print(f"[{get_current_utc_str()}] Entering main loop...")
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            # Catch unexpected errors in the loop so the script doesn't crash and trigger a restart storm
            print(f"[{get_current_utc_str()}] [ERROR] Unexpected error in main loop: {e}")
            time.sleep(10)