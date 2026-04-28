# Linode Billing Analysis Tool 📊

A professional Streamlit-based dashboard designed to audit and visualize Linode (Akamai Cloud) billing data. This tool translates complex, line-by-line CSV logs into actionable insights, helping users verify costs and understand infrastructure trends.

## ✨ Key Features

* **Hourly Machine Quantity Stats**: Calculates exactly how many concurrent machines were online at any given hour based on machine type and data center (Region). Visualized on an interactive step chart.
* **Daily Average Footprint**: Aggregates hourly data to calculate the exact daily average of running machines (Total hours per day / 24, rounded down). Perfect for tracking the scale of LKE auto-scaling nodes.
* **Smart Prorated Traffic Auditing**: 
  * Provides clear visibility into overall network traffic consumption.
  * Precisely calculates both the free included traffic quotas (prorated by machine uptime) and the billed overage traffic

---

## 🛠️ Installation & Deployment

### Local Setup
1. **Install Python**: Ensure you have Python 3.8 or newer installed on your local machine.
2. **Install Dependencies**: Open your terminal or command prompt and run:
```bash
   pip install streamlit pandas plotly numpy
```
3. **Save the Code**: Save the provided script as linode_billing_analysis.py.
4. **Run the App**: Navigate to the folder where you saved the file and execute:
```bash
   streamlit run linode_billing_analysis.py
```
## 📖 How to Use
1. **Download CSV**: The monthly billing CSV file can be downloaded directly from admin.linode.com, or requested from your Akamai Partner.

2. **Upload**: Upload the CSV into the sidebar of the tool.

3. **Analyze**: Click **Generate Cross-Statistics Charts** to start.
