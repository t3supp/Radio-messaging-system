import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import io
import time

# --- Google Sheets Setup ---
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]

creds_dict = st.secrets["gcp_service_account"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

sheet = client.open("Radio Messages").sheet1

# --- Message Functions ---
def add_message(sender, message, section, status="Logged"):
    time_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([sender, message, section, status, time_stamp, ""])

def get_messages():
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def update_status(msg_id, new_status):
    df = get_messages()
    if msg_id <= len(df):
        sheet.update_cell(msg_id + 1, 4, new_status)
        return True
    return False

def get_new_message_counts():
    df = get_messages()
    counts = df[df["Status"] == "Logged"]["Section"].value_counts().to_dict()
    return counts

def add_comment(msg_id, comment, section):
    df = get_messages()
    if msg_id <= len(df):
        existing_comment = sheet.cell(msg_id + 1, 6).value
        new_comment = f"{existing_comment}\n[{section}] {comment}" if existing_comment else f"[{section}] {comment}"
        sheet.update_cell(msg_id + 1, 6, new_comment)
        return True
    return False

def edit_comment(msg_id, new_comment):
    df = get_messages()
    if msg_id <= len(df):
        sheet.update_cell(msg_id + 1, 6, new_comment)
        return True
    return False

def delete_message(msg_id):
    df = get_messages()
    if msg_id <= len(df):
        sheet.delete_rows(msg_id + 1)
        return True
    return False

# --- Authentication ---
users = {
    "admin": {"password": "admin123", "role": "Admin"},
    "commander": {"password": "cmd123", "role": "Commander"},
    "exo": {"password": "exo123", "role": "EX-O"},
    "s1": {"password": "s1pass", "role": "S1"},
    "s2": {"password": "s2pass", "role": "S2"},
    "s3": {"password": "s3pass", "role": "S3"},
    "s4": {"password": "s4pass", "role": "S4"},
    "s5": {"password": "s5pass", "role": "S5"},
    "s6": {"password": "s6pass", "role": "S6"},
    "s7": {"password": "s7pass", "role": "S7"},
    "hq": {"password": "hqpass", "role": "HQ"},
}

def login(username, password):
    username = username.lower().strip()
    password = password.strip()
    if username in users and users[username]["password"] == password:
        return users[username]["role"]
    return None

# --- Streamlit App ---
st.title("📡 Battalion Radio Messaging System (Unified Dashboard)")

# Auto-refresh every 5 minutes
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()
if time.time() - st.session_state.last_refresh > 300:
    st.session_state.last_refresh = time.time()
    st.rerun()

if "role" not in st.session_state:
    st.subheader("Login")
    username = st.text_input("Username").strip()
    password = st.text_input("Password", type="password").strip()
    if st.button("Login"):
        role = login(username, password)
        if role:
            st.session_state.role = role
            st.success(f"Logged in as {role}")
            st.rerun()
        else:
            st.error("Invalid credentials")

else:
    role = st.session_state.role

    # --- Notifications ---
    if "notif_count" not in st.session_state:
        st.session_state.notif_count = 0

    st.markdown(f"🔔 Notifications: **{st.session_state.notif_count}**")
    if st.button("View Notifications"):
        df = get_messages()
        new_msgs = df.tail(st.session_state.notif_count)
        st.dataframe(new_msgs)
        st.session_state.notif_count = 0

    # --- Unified Dashboard ---
    df = get_messages()

    def color_status(val):
        if val == "Logged":
            return "background-color: lightblue"
        elif val == "Action Ongoing":
            return "background-color: khaki"
        elif val == "Completed":
            return "background-color: lightgreen"
        return ""
    st.dataframe(df.style.applymap(color_status, subset=["Status"]), use_container_width=True)

    # --- Status Editing (all roles) ---
    st.subheader("Update Message Status")
    msg_id = st.number_input("Message ID to update status", min_value=1, step=1)
    new_status = st.selectbox("New Status", ["Logged", "Action Ongoing", "Completed"])
    if st.button("Update Status"):
        if update_status(msg_id, new_status):
            st.success("Message status updated!")
        else:
            st.error("Invalid Message ID")

    # --- Commenting (all roles) ---
    st.subheader("Add Comment")
    msg_id_comment = st.number_input("Message ID to comment", min_value=1, step=1)
    comment = st.text_area("Add Comment")
    if st.button("Submit Comment"):
        if add_comment(msg_id_comment, comment, role):
            st.success("Comment added!")
        else:
            st.error("Invalid Message ID")

    # --- Full Control Roles ---
    if role in ["Admin", "Commander", "EX-O", "S6"]:
        st.subheader(f"{role} Controls")

        # Upload message (Admin only)
        if role == "Admin":
            st.subheader("Upload Radio Message")
            sender = st.text_input("Sender")
            message = st.text_area("Message")
            section = st.selectbox("Assign to Section", ["S1","S2","S3","S4","S5","S6","S7","HQ"])
            if st.button("Submit Message"):
                add_message(sender, message, section)
                st.success("Message uploaded!")
                st.session_state.notif_count += 1

        # Edit comment
        edit_id = st.number_input("Message ID to edit comment", min_value=1, step=1)
        new_comment = st.text_area("Edit Comment (Full Control)")
        if st.button("Update Comment (Full Control)"):
            if edit_comment(edit_id, new_comment):
                st.success("Comment updated!")
            else:
                st.error("Invalid Message ID")

        # Delete message
        delete_id = st.number_input("Message ID to delete", min_value=1, step=1)
        if st.button("Delete Message"):
            if delete_message(delete_id):
                st.success("Message deleted!")
            else:
                st.error("Invalid Message ID")

        # Export logs
        st.subheader("📤 Export Logs")
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)
        st.download_button(
            label="Download Excel File",
            data=buffer,
            file_name=f"radio_logs_{role.lower()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )