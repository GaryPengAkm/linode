# 🚀 Linode Critical Event Monitor Tool

This tool push specific instance state changes (like `linode_reboot` or `linode_shutdown`) directly to third-party collaboration tools like Feishu or Lark.


## ✨Key Features

* **Automated API Polling**: Runs as a background service, polling the Linode API every 120 seconds (configurable via `POLL_INTERVAL`).
* **Targeted Event Filtering**: Specifically monitors 5 types of critical infrastructure actions:
    * `host_reboot` (Host-initiated reboot)
    * `lassie_reboot` (Lassie watchdog automated reboot)
    * `linode_reboot` (User-initiated reboot)
    * `linode_shutdown` (Power off)
    * `linode_boot` (Power on)
      
   **You can customize the above Event-types as you need**
* **State Tracking (Checkpointing)**: Uses a local `last_event_id.txt` file to store the ID of the last processed event. This ensures:
    * No duplicate alerts are sent if the script restarts.
    * Historical events are skipped on the first run to prevent alert spam.
* **Feishu/Lark Integration**: Sends beautifully formatted messages including the action type, user, timestamp, status, entity label, and a direct URL to the instance.

## 🛠️ Installation & Usage

### Prerequisites
* Python 3.x
* Python `requests` library

### Configuration
Open `linode_critical_event_monitor.py` and update the following variables with your credentials:

```python
TOKEN = "Bearer <your_linode_api_token>"
FEISHU_WEBHOOK = "[https://open.feishu.cn/open-apis/bot/v2/hook/](https://open.feishu.cn/open-apis/bot/v2/hook/)<your_hook_id>"
```
Important:
Your Linode API Token must have Events: Read-Only scope.
Ensure your Feishu bot has a Custom Keyword (e.g., "Linode" or "Alert") configured to match the message payload for security.
## 📦 Deployment
### Running Manually (Testing)
python3 linode_critical_event_monitor.py
### Running as a systemd Service (Production)
#### Create the service file linode-monitor.service
#### Enable and start the service:
```
sudo systemctl daemon-reload
sudo systemctl enable linode-monitor
sudo systemctl start linode-monitor
```
## 📝 Logging
You can monitor the service activity in real-time using journalctl:
journalctl -u linode-monitor -f
