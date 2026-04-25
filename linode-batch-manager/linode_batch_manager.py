import streamlit as st
from linode_api4 import LinodeClient
import os
import time

# Define the file path for storing the Token
TOKEN_FILE = ".linode_token"

st.set_page_config(page_title="Linode Management Assistant", layout="wide", page_icon="⚙️")

# ==========================================
# Custom CSS Injection for better visibility
# ==========================================
def inject_custom_css():
    st.markdown(
        """
        <style>
            /* 1. Global Font Size */
            html, body, [class*="css"], .stMarkdown, p, li {
                font-size: 18px !important;
            }

            /* 2. Make Widget Labels bold and larger */
            label[data-testid="stWidgetLabel"] p {
                font-size: 20px !important;
                font-weight: bold !important;
                color: #31333F !important;
            }

            /* 3. Button Styling: Extra bold, black text, white background, larger font */
            div.stButton > button {
                font-size: 24px !important;  /* Increased font size for better visibility */
                font-weight: 900 !important; /* Maximum bold weight */
                color: #000000 !important;   /* Pure black text */
                background-color: #FFFFFF !important; /* White background */
                border: 2px solid #000000 !important; /* Black border */
                padding: 12px 24px !important; /* Adjusted padding for larger text */
                height: auto !important;
            }
            
            /* Special handling for Primary buttons (e.g., Delete button) */
            div.stButton > button[kind="primary"] {
                background-color: #FF4B4B !important; /* Keep red background for dangerous actions */
                color: #000000 !important;
            }

            /* 4. Sidebar Font Size */
            section[data-testid="stSidebar"] .stMarkdown p, 
            section[data-testid="stSidebar"] label p {
                font-size: 18px !important;
            }

            /* 5. Input Field Font Size */
            input {
                font-size: 18px !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

# Execute CSS injection
inject_custom_css()

# ==========================================
# 1. Token Management & Dynamic UI Logic
# ==========================================
def load_token():
    """Load Token from a local file"""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            return f.read().strip()
    return ""

def save_token(token_str):
    """Save Token to a local file"""
    with open(TOKEN_FILE, "w") as f:
        f.write(token_str)

# Initialize Session State
if "linode_token" not in st.session_state:
    st.session_state.linode_token = load_token()

st.sidebar.header("⚙️ Global Settings")

if not st.session_state.linode_token:
    # State A: No Token, display input field
    token_input = st.sidebar.text_input(
        "Enter Linode API Token", 
        type="password",
        help="The Token will be saved locally in the .linode_token file"
    )
    
    if st.sidebar.button("Save and Apply Token"):
        if token_input.strip():
            save_token(token_input)
            st.session_state.linode_token = token_input
            st.rerun()
        else:
            st.sidebar.warning("Token cannot be empty!")
            
    st.warning("👈 Please enter your API Token in the left sidebar and click save to start.")
    st.stop()
else:
    # State B: Token exists, hide input field, display exit mechanism
    st.sidebar.success("✅ API Token Configured")
    if st.sidebar.button("Clear / Change Token"):
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
        st.session_state.linode_token = ""
        st.rerun()

st.sidebar.markdown("---")

# ==========================================
# 2. Navigation & Routing
# ==========================================
menu = st.sidebar.radio(
    "📌 Navigation", 
    ["🔌 Batch Lifecycle Management", "🚀 Batch Clone & Deployment"]
)

# Initialize the client using the saved Token
client = LinodeClient(st.session_state.linode_token)

# ==========================================
# 3. Feature Module: Batch Lifecycle Management
# ==========================================
if menu == "🔌 Batch Lifecycle Management":
    st.title("🔌 Linode Batch Lifecycle Management")
    
    try:
        with st.spinner("Loading your Linode instances..."):
            instances = client.linode.instances()
            instance_options = {}
            for i in instances:
                ip_addr = i.ipv4[0] if i.ipv4 else "No IP"
                status_emoji = "🟢" if i.status == "running" else ("🔴" if i.status == "offline" else "🟡")
                label = f"{status_emoji} {i.label} | IP: {ip_addr} | Status: {i.status}"
                instance_options[label] = i.id
                
    except Exception as e:
        st.error(f"Failed to connect to the Linode API: {e}")
        st.stop()

    if not instance_options:
        st.info("No manageable instances found.")
        st.stop()

    st.markdown("### 🔍 Filter and Select")
    search_query = st.text_input("Step 1: Enter a keyword to filter instances")

    # Execute filtering logic based on user input
    filtered_options = {
        label: instance_id 
        for label, instance_id in instance_options.items() 
        if search_query.lower() in label.lower()
    }

    # Display matching instances in real-time
    if search_query:
        if filtered_options:
            st.write(f"✅ Found **{len(filtered_options)}** matching instance(s):")
            matched_names = "\n".join([f"• {name}" for name in filtered_options.keys()])
            st.info(matched_names)
        else:
            st.warning(f"❌ No instances found containing '{search_query}'.")
            st.stop()

    st.markdown("---")
    st.markdown("##### Step 2: Confirm Selection")

    select_all = st.checkbox(f"Select all {len(filtered_options)} matched instance(s)")

    if select_all:
        selected_labels = st.multiselect(
            "Final confirmed targets", 
            options=list(filtered_options.keys()), 
            default=list(filtered_options.keys()), 
            disabled=True
        )
    else:
        selected_labels = st.multiselect(
            "Check instances to operate on", 
            options=list(filtered_options.keys())
        )

    selected_ids = [filtered_options[label] for label in selected_labels]

    st.markdown("---")

    def execute_batch(action_name, endpoint_suffix, method="POST"):
        if not selected_ids:
            st.warning("Please select instances first!")
            return

        progress_bar = st.progress(0)
        status_text = st.empty()
        success_count = 0
        
        total = len(selected_ids)
        for index, instance_id in enumerate(selected_ids):
            status_text.text(f"Sending [{action_name}] to instance {instance_id}...")
            try:
                url = f"/linode/instances/{instance_id}{endpoint_suffix}"
                if method == "POST":
                    client.post(url)
                elif method == "DELETE":
                    client.delete(url)
                success_count += 1
            except Exception as e:
                st.error(f"Failed for {instance_id}: {e}")
                
            progress_bar.progress((index + 1) / total)
            time.sleep(0.5)

        status_text.empty()
        if success_count > 0:
            st.success(f"🎉 Batch [{action_name}] submitted ({success_count}/{total}).")
            if st.button("🔄 Refresh Status"):
                st.rerun()

    st.subheader("⚡ Batch Execution")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🟢 Batch PowerOn", use_container_width=True):
            execute_batch("Boot", "/boot", "POST")
    with col2:
        if st.button("🔴 Batch Shutdown", use_container_width=True):
            execute_batch("Shutdown", "/shutdown", "POST")
    with col3:
        if st.button("🟡 Batch Reboot", use_container_width=True):
            execute_batch("Reboot", "/reboot", "POST")

    st.markdown("---")
    st.subheader("⚠️ High-Risk Batch Delete")
    st.error("Delete operation is IRREVERSIBLE!")
    confirm_delete = st.checkbox("Confirm permanent deletion")
    
    # Kept type="primary" here so the delete button stays red for safety
    if st.button("🗑️ Batch Delete", type="primary", disabled=not confirm_delete, use_container_width=True):
        execute_batch("Delete", "", "DELETE")

# ==========================================
# 4. Feature Module: Batch Clone & Deployment
# ==========================================
elif menu == "🚀 Batch Clone & Deployment":
    st.title("🚀 Linode Batch Clone & Deployment Tool")
    
    try:
        with st.spinner("Loading Linode data..."):
            instances = client.linode.instances()
            instance_options = {f"{i.label} ({i.id})": i.id for i in instances}
            images = client.images()
            image_options = {f"🔒 Private | {img.label} ({img.id})": img.id for img in images if not img.is_public}
            regions = client.regions()
            region_options = {r.id: f"{r.label} ({r.id})" for r in regions}
            types = client.linode.types()
            type_options = {t.id: f"{t.label} - {t.id}" for t in types}
    except Exception as e:
        st.error(f"API Connection Failed: {e}")
        st.stop()

    st.header("Clone / Deploy Instances")
    source_type = st.radio("1. Select Source Type", ["Existing Instance", "Existing Private Image"], horizontal=True)

    col1, col2 = st.columns(2)
    with col1:
        if source_type == "Existing Instance":
            if not instance_options:
                st.warning("No available instances.")
                source_id = None
            else:
                source_label = st.selectbox("2. Select Source Linode", options=list(instance_options.keys()))
                source_id = instance_options[source_label]
            root_pass = None 
        else:
            if not image_options:
                st.warning("No available private images.")
                source_id = None
            else:
                source_label = st.selectbox("2. Select Source Image", options=list(image_options.keys()))
                source_id = image_options[source_label]
            root_pass = st.text_input("🔑 Root Password (Required)", type="password")
        
        count = st.number_input("3. Creation Count", min_value=1, max_value=20, value=1)
        prefix = st.text_input("4. Name Prefix", value="cloned-node")
        
    with col2:
        selected_region_id = st.selectbox("5. Target Region", options=list(region_options.keys()), format_func=lambda x: region_options[x])
        selected_type_id = st.selectbox("6. Instance Type", options=list(type_options.keys()), format_func=lambda x: type_options[x])

    # Pre-submission validation
    disable_button = False
    if source_type == "Existing Private Image":
        if not root_pass:
            disable_button = True
        if not image_options:
            disable_button = True
    elif not instance_options:
        disable_button = True

    # Removed type="primary" to apply the white background CSS
    if st.button("🟢 Start Batch Clone & Deployment", disabled=disable_button, use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()
        success_count = 0
        for i in range(count):
            new_label = f"{prefix}-{i+1}"
            status_text.text(f"Submitting: {new_label}...")
            try:
                if source_type == "Existing Instance":
                    client.post(f"/linode/instances/{source_id}/clone", data={"region": selected_region_id, "type": selected_type_id, "label": new_label})
                else:
                    client.post("/linode/instances", data={"region": selected_region_id, "type": selected_type_id, "label": new_label, "image": source_id, "root_pass": root_pass})
                success_count += 1
            except Exception as e:
                st.error(f"Failed for {new_label}: {e}")
            progress_bar.progress((i + 1) / count)
        status_text.empty()
        if success_count > 0:
            st.success("🎉 Tasks submitted. Check Linode Manager for progress.")