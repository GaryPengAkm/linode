# Linode Batch Management 

A powerful, Python-based GUI tool designed to bring efficient **batch operations** to the Linode (Akamai) ecosystem.

## 🚀 Core Features

### 🔌 Batch Lifecycle Management
- **Bulk Power Control**: Boot, Shutdown, or Reboot multiple selected instances with one click.
- **Status Visualization**: Real-time status indicators (🟢 Running / 🔴 Offline / 🟡 Transitioning) and IP address display.
- **High-Risk Protection**: A confirmation lock for the Batch Delete feature to prevent accidental data loss.

### 🚀 Batch Clone & Deployment
- **Instance Cloning**: Use an existing instance as a source to create N identical clones.
- **Image Deployment**: Bulk deploy instances from your **Private Images** (Root password required).
- **Custom Configuration**: Select target Regions and Instance Types (Plans) dynamically during deployment.

### 🔍 Smart Filtering & Selection
- **Real-time Filtering**: Search and filter instances by name in real-time.
- **Select All**: Quickly select all matching search results to handle dozens of machines in seconds.

### 🛡️ Safety & UI Design
- **Token Persistence**: Your API Token is stored locally in a hidden `.linode_token` file—no need to re-type it every time.
- **Enhanced UI**: Custom CSS with large fonts and bold, high-contrast buttons for clear and error-free management.
- **API Rate-Limit Safety**: Built-in request pacing to prevent triggering Linode API rate limits.

---

## 🛠️ Installation & Deployment

### Prerequisites
- **Python 3.8+** installed.
- A **Linode Personal Access Token** (with Read/Write permissions for Linodes).

### Step 1: Install Dependencies


It is recommended to use a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\\Scripts\\activate  # Windows
pip install streamlit linode_api4
```

### Step 2: Run the Application

Save the script as `linode-batch-manager.py` and execute:

```bash
streamlit run linode-batch-manager.py
```
The interface will automatically open in your default browser at `http://localhost:8501`.

### Step 3: Configure Token
1. Go to **Global Settings** in the left sidebar.
2. Enter your Linode API Token and click **Save and Apply Token**.
3. Once verified, the input field will hide, and your instance list will appear.
