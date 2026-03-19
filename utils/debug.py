import streamlit as st
import sys
import os
from datetime import datetime

class DebugManager:
    def __init__(self):
        self.logs = []
        self.api_responses = {}
        self.status = {}

    def log(self, level, msg, details=None):
        self.logs.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "level": level,
            "msg": msg,
            "details": details
        })

    def set_status(self, key, value):
        self.status[key] = value

    def set_api(self, key, value):
        self.api_responses[key] = value

    def render(self):
        if not st.sidebar.checkbox("🔧 Show Debug Info"):
            return

        st.sidebar.markdown("---")
        st.sidebar.subheader("🐛 Debug Console")

        # 🔹 System Status
        st.sidebar.markdown("### 📊 System Status")

        for key, value in self.status.items():
            icon = "✅" if value else "🔴"
            st.sidebar.markdown(f"{icon} {key}: {value}")

        # 🔹 Logs
        st.sidebar.markdown("### 📝 Logs")
        for log in self.logs[-10:]:
            icon = {
                "ERROR": "🔴",
                "WARNING": "🟡",
                "SUCCESS": "✅"
            }.get(log["level"], "⚪")

            st.sidebar.markdown(f"{icon} {log['time']} - {log['msg']}")

        # 🔹 API Response Viewer
        with st.sidebar.expander("📦 API Responses"):
            for key, value in self.api_responses.items():
                st.markdown(f"**{key}**")
                st.json(value)

        # 🔹 Import Check
        with st.sidebar.expander("📦 Import Check"):
            try:
                import core.dhan_api
                st.success("core.dhan_api OK")
            except:
                st.error("core.dhan_api FAILED")

            try:
                import utils.helpers
                st.success("utils.helpers OK")
            except:
                st.error("utils.helpers FAILED")

        # 🔹 Time Info
        st.sidebar.markdown("### ⏱ Time")
        st.sidebar.write(datetime.now().strftime("%H:%M:%S"))
