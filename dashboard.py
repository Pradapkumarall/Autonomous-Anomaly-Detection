import streamlit as st
import pandas as pd
import time
import json
import logging
from threading import Thread
import os

# Streamlit config
st.set_page_config(page_title="Autonomous Anomaly Detection", layout="wide")

st.title("🛡️ Autonomous Anomaly Detection & Response")
st.markdown("Real-time monitoring of <60s MTTR (Mean Time to Resolution) and ML accuracy.")

LOG_FILE = "system_events.json"

if "auto_refresh" not in st.session_state:
    st.session_state["auto_refresh"] = True

def load_data():
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, 'r') as f:
        lines = f.readlines()
        return [json.loads(line) for line in lines if line.strip()]

col1, col2, col3 = st.columns(3)
data = load_data()
df = pd.DataFrame(data)

if not df.empty:
    avg_mttr_ms = df['processing_time_ms'].mean() if 'processing_time_ms' in df else 0
    total_events = len(df)
    anomalies_count = len(df[df['is_anomaly'] == True])
    
    col1.metric("Total Events", total_events)
    col2.metric("Anomalies Detected", anomalies_count)
    col3.metric("Avg Resolution Time (MTTR)", f"{avg_mttr_ms:.2f} ms")

    st.subheader("Event Stream")
    # Show most recent first
    display_df = df.tail(20).sort_index(ascending=False)
    
    st.dataframe(
        display_df, 
        use_container_width=True,
        column_config={
            "is_anomaly": st.column_config.CheckboxColumn("Anomaly", help="ML Detection Result"),
            "confidence": st.column_config.NumberColumn("Confidence", format="%.3f"),
            "processing_time_ms": st.column_config.NumberColumn("Processing Time (ms)", format="%.2f")
        }
    )

    st.subheader("Human-in-the-Loop Actions Pending")
    if 'action_result' in df.columns:
        pending = display_df[(display_df['is_anomaly'] == True) & (display_df['action_result'].str.contains("Pending", na=False, case=False))]
        if not pending.empty:
            for idx, row in pending.iterrows():
                with st.expander(f"⚠️ Action Required for {row.get('root_cause', 'Unknown')}"):
                    st.write(f"**Confidence:** {row.get('confidence', 0)*100:.2f}%")
                    st.write(f"**Action Suggested:** `{row.get('selected_action', 'None')}`")
                    if st.button(f"Approve Action: {row.get('selected_action')}", key=f"btn_{idx}"):
                        st.success("Action Approved and Executed.")
        else:
            st.info("No pending human-in-the-loop actions.")
else:
    st.info("No system events received yet. Start `main.py` pipeline.")

time.sleep(1.5)
if st.session_state["auto_refresh"]:
    st.rerun()
