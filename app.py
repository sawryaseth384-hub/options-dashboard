You are modifying an existing Python Dash app.

STRICT RULES (VERY IMPORTANT):

- DO NOT delete any existing code
- DO NOT replace existing functions
- DO NOT change UI layout
- DO NOT rename variables
- ONLY ADD new code safely
- Existing dashboard must keep working exactly same

---

GOAL:
Add DEBUG VIEW to show ALL API responses (LTP, Expiry, Option Chain)

---

TASK:

1. ADD RAW JSON PANEL

Add this at the bottom of existing layout (DO NOT modify layout structure):

html.H3("DEBUG API DATA"),
html.Pre(id="raw-json", style={
"height": "300px",
"overflow": "scroll",
"backgroundColor": "black",
"color": "lime",
"padding": "10px"
})

---

2. MODIFY MAIN CALLBACK

Find existing main callback (the one updating LTP + table)

ADD one more output:

Output("raw-json", "children")

DO NOT remove existing outputs

---

3. ADD RAW RESPONSE STORAGE

Inside callback, at top:

raw_output = ""

---

4. CAPTURE API RESPONSES

After each API call:

raw_output += "\n\n--- LTP RESPONSE ---\n"
raw_output += response.text

raw_output += "\n\n--- EXPIRY RESPONSE ---\n"
raw_output += expiry_response.text

raw_output += "\n\n--- OPTION CHAIN RESPONSE ---\n"
raw_output += chain_response.text

---

5. ADD ERROR LOGGING

Inside exception:

raw_output += "\n\nERROR:\n" + str(e)

---

6. RETURN UPDATED OUTPUT

At the end of callback:

return existing_outputs..., raw_output

(IMPORTANT: Keep existing outputs SAME order + add raw_output at end)

---

7. DO NOT TOUCH:

- UI structure
- Existing dropdowns
- Existing logic
- Existing API calls

---

FINAL RESULT:

Dashboard should now show:

- Existing UI (unchanged)
- AND a debug panel showing FULL API responses

---
