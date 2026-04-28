#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import os
import time
from datetime import datetime

# --- Configuration ---
TOKEN = "Bearer Your_Token"
FEISHU_WEBHOOK = "Your_Webhook"
API_URL = "https://api.linode.com/v4/account/events?page={page}&page_size=25"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LAST_ID_FILE = os.path.join(SCRIPT_DIR, "last_event_id.txt")

# Action List to monitor
ACTION_LIST = [
    "host_reboot", "lassie_reboot", "linode_reboot", 
    "linode_shutdown", "linode_boot"
]
POLL_INTERVAL = 120  # Seconds between checks


def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def get_last_event_id():
    if os.path.exists(LAST_ID_FILE):
        try:
            with open(LAST_ID_FILE, "r") as f:
                return int(f.read().strip())
        except (ValueError, IOError):
            return 0
    return 0


def save_last_event_id(event_id):
    with open(LAST_ID_FILE, "w") as f:
        f.write(str(event_id))


def send_feishu(msg):
    payload = {
        "msg_type": "text",
        "content": {"text": msg}
    }
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(FEISHU_WEBHOOK, headers=headers, data=json.dumps(payload), timeout=10)
        result = response.json()
        
        # Feishu returns "code": 0 upon success. 
        # If it's a Keyword mismatch, it returns an error code like 94004
        if result.get("code") == 0:
            return True
        else:
            log(f"[FEISHU REJECTED] Feishu refused the message (Check Custom Keywords). Response: {result}")
            return False
            
    except Exception as e:
        log(f"[ERROR] Network error sending to Feishu: {e}")
        return False


def check_events():
    headers = {
        "Accept": "application/json",
        "Authorization": TOKEN
    }

    last_id = get_last_event_id()
    max_id_seen = last_id
    page = 1
    new_events = []

    log(f"[INFO] Polling Linode API... (Current Base ID: {last_id})")

    while True:
        url = API_URL.format(page=page)
        try:
            res = requests.get(url, headers=headers, timeout=15)
            res.raise_for_status()
            events = res.json().get("data", [])
        except Exception as e:
            log(f"[ERROR] Linode API Request Error: {e}")
            break

        if not events:
            break

        for event in events:
            eid = event["id"]
            
            # Initial Run Strategy
            if last_id == 0:
                max_id_seen = eid
                log(f"[INIT] First run detected. Setting baseline ID: {eid}. Skipping historical events.")
                break
                
            if eid <= last_id:
                break 
                
            max_id_seen = max(max_id_seen, eid)
            
            # Print ALL new events to terminal for debugging
            log(f"[DEBUG] Raw Event Found -> ID: {eid} | Action: {event['action']} | Status: {event['status']}")
            
            if event["action"] in ACTION_LIST:
                new_events.append(event)

        if any(e["id"] <= last_id for e in events) or last_id == 0:
            break
        page += 1

    # Sort from oldest to newest for chronological alerting
    new_events.sort(key=lambda e: e["id"])

    for event in new_events:
        # Safely extract entity info to prevent NoneType crashes
        entity = event.get('entity') or {}
        entity_type = entity.get('type', 'N/A')
        entity_label = entity.get('label', 'Unknown')
        entity_id = entity.get('id', '')
        
        msg = (
            f"🚨 Linode Alert Notification\n"
            f"Action: {event['action']}\n"
            f"User: {event['username']}\n"
            f"Time: {event['created']}\n"
            f"Status: {event['status']}\n"
            f"Entity: {entity_type} - {entity_label}\n"
            f"URL: https://cloud.linode.com/linodes/{entity_id}"
        )
        
        if send_feishu(msg):
            log(f"[SUCCESS] Alert delivered to Feishu for Event ID: {event['id']}")
        else:
            log(f"[FAIL] Could not deliver alert for Event ID: {event['id']}")

    if max_id_seen > last_id:
        save_last_event_id(max_id_seen)
        log(f"[INFO] Checkpoint updated to ID: {max_id_seen}")


def main():
    log("=== Starting Linode Event Monitor Service ===")
    while True:
        try:
            check_events()
        except Exception as e:
            log(f"[CRITICAL] Unexpected loop error: {e}")
        
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()