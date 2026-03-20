import streamlit as st

def render_debug_panel():
    show_debug = st.sidebar.checkbox("🔧 Debug Panel")

    if not show_debug:
        return

    st.sidebar.markdown("## 📊 Development Status")

    st.sidebar.markdown("""
### ✅ Level 1 – Complete
- Option Chain
- Expiry
- Spot
- Delta

---

### ⬜ Level 2 – Pending
- PCR
- Support / Resistance
- Strike Range
- Auto Refresh

---

### ⬜ Level 3 – Pending
- OI Change
- IV
- ATM
- Call vs Put

---

### ⬜ Level 4 – Advanced
- Heatmap
- Signal
- Trend
- MTF

---

### ⬜ Level 5 – Elite
- Strategy Builder
- Payoff Graph
- Greeks Analysis
- AI Engine

---

### ⚡ API Limits
- Option Chain → 1 req / 3 sec
""")
