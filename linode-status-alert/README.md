# 🚀 Key Features

* **Unified Monitoring**: Tracks both **Unresolved Incidents** (unexpected outages) and **Scheduled Maintenances** (planned work).
* **Precision Filtering**: Supports filtering by **Component Name** (e.g., specific datacenters like `sg-sin-2`) and **Impact Level** (e.g., only `major` or `critical` events) to reduce alert fatigue.
* **Automated Briefings**: Sends recurring Daily (24-hour lookahead) and Weekly (7-day lookahead) maintenance overviews.
* **Smart Deduplication**: Uses a local state file to track alerted incidents, ensuring you are notified only once per event state change.
* **Fault Tolerance**: Built-in error handling for API timeouts and network jitter, ensuring 24/7 reliability.

---

# 🛠 Prerequisites

* **Python**: 3.7+
* **Libraries**: `requests`, `schedule`
* **Access**: A Feishu/Lark Bot Webhook URL with a security keyword (e.g., "Linode").

---

# 📦 Installation & Deployment

## 1. Environment Setup
We recommend using a Python virtual environment to isolate dependencies.


### Create directory and virtual environment
mkdir -p /root/linode-status-alert
cd /root/linode-status-alert
python3 -m venv venv

### Activate and install requirements
source venv/bin/activate
pip install requests schedule

## 2. Configuration
Edit the Configuration Area inside linode_monitor.py:

FEISHU_URL: Your bot's webhook URL.

KEYWORD: Your bot's security keyword.

INCIDENT_COMPONENTS: List of components to monitor (leave empty [] for all).

MAINTENANCE_COMPONENTS: List of components for maintenance alerts.

**Refer to linode_components.txt for the component name**

## 3. Deploy as a System Service
To ensure the script runs continuously and survives reboots, use systemd.

### Create the service file:
  nano /etc/systemd/system/linode-status-alert.service
  Paste the following:
 ```  
      [Unit]
      Description=Linode Feishu Monitor Service
      After=network-online.target

      [Service]
      Type=simple
      User=root
      WorkingDirectory=/root/linode-status-alert/
      ExecStart=/root/linode-status-alert/venv/bin/python3 /root/linode-status-alert/linode_status_alert.py
      Restart=always
      RestartSec=10
      
      [Install]
      WantedBy=multi-user.target
```
 
### Start the service:

systemctl daemon-reload
systemctl enable linode-status-alert.service
systemctl start linode-status-alert.service

# 📊 Monitoring
Check the logs in real-time to verify the script is polling correctly:
journalctl -u linode-status-alert.service -f
