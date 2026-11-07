"""
Talk2Task – Smart To-Do Extractor
Final Build: Working Buttons, CSV Export, Calendar (.ics) Export
"""

import pandas as pd
import streamlit as st
import altair as alt
import uuid
from datetime import datetime
from task_extractor import extract_tasks
import auth_manager as auth

# ----------------------------------------------------------------------
# Page Configuration & CSS
# ----------------------------------------------------------------------
st.set_page_config(page_title="Talk2Task", page_icon="✦", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    :root {
        --bg: #F0F5F4; --sidebar-bg: #F7FCFB; --card-bg: #FFFFFF; --border: #D6E4E1;
        --text: #2C423D; --muted: #6B857F; --brand: #4A7C71;
        --high: #D9534F; --med: #F0AD4E; --low: #5CB85C;
    }
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: var(--text); }
    .stApp { background: var(--bg); }
    #MainMenu, footer, header {visibility: hidden;}
    .block-container { padding-top: 2rem; padding-bottom: 4rem; max-width: 1200px; }
    
    /* Sidebar */
    section[data-testid="stSidebar"] { background-color: var(--sidebar-bg) !important; border-right: 1px solid var(--border); }
    div[role="radiogroup"] > label > div:first-child { display: none !important; }
    div[role="radiogroup"] > label { padding: 12px 16px !important; border-radius: 8px !important; border: 1px solid transparent !important; margin-bottom: 4px !important; cursor: pointer !important; transition: all 0.2s !important; }
    div[role="radiogroup"] > label:hover { background-color: var(--bg) !important; }
    div[role="radiogroup"] > label[data-checked="true"] { background-color: var(--bg) !important; border-color: var(--brand) !important; }
    div[role="radiogroup"] > label[data-checked="true"] p { color: var(--brand) !important; font-weight: 600 !important; }
    div[role="radiogroup"] p { font-size: 0.95rem !important; font-weight: 500 !important; color: var(--text) !important; }

    /* UI Elements */
    .brand { display: flex; align-items: center; gap: 10px; font-weight: 800; font-size: 1.5rem; color: var(--brand); padding: 0 16px 10px 16px; }
    .brand-sub { padding: 0 16px 20px 16px; color: var(--muted); font-size: 0.9rem; }
    .hero { background: linear-gradient(135deg, #E2F0EA 0%, #D0E5DF 100%); border-radius: 16px; padding: 40px; margin-bottom: 30px; text-align: center; border: 1px solid var(--border); }
    .hero h1 { font-size: 2.2rem; margin: 0 0 10px; color: var(--text); font-weight: 800; }
    .hero p { color: var(--muted); font-size: 1.1rem; margin: 0; }
    
    .metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 30px; }
    .metric { background: var(--card-bg); border: 1px solid var(--border); border-radius: 16px; padding: 24px; text-align: center; }
    .metric .value { font-size: 2rem; font-weight: 800; color: var(--text); line-height: 1; margin-bottom: 8px; }
    .metric .label { font-size: .75rem; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); font-weight: 700; }
    .v-blue { color: var(--brand); } .v-red { color: var(--high); } .v-green { color: var(--low); } .v-amber { color: var(--med); }

    /* Native Streamlit Container styling for Cards */
    div[data-testid="stVerticalBlock"] > div[style*="border"] {
        background-color: var(--card-bg) !important;
        border: 1px solid var(--border) !important;
        border-left: 4px solid var(--brand) !important;
        border-radius: 12px !important;
        padding: 16px 20px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02) !important;
        margin-bottom: 8px;
    }
    
    .badge { background: var(--bg); color: var(--brand); padding: 6px 12px; border-radius: 8px; font-size: 0.75rem; font-weight: 700; border: 1px solid var(--border); display: inline-block; white-space: nowrap; }
    .badge-done { background: #E8F5E9; color: #2E7D32; }
    </style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------
# State Management
# ----------------------------------------------------------------------
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "username" not in st.session_state: st.session_state.username = ""
if "role" not in st.session_state: st.session_state.role = ""
if "nav" not in st.session_state: st.session_state.nav = "Home Dashboard"
if "focus_idx" not in st.session_state: st.session_state.focus_idx = 0
if "raw_text" not in st.session_state: st.session_state.raw_text = ""

SAMPLE_TEXT = "Hello team, please complete the project documentation by Friday. Call the client tomorrow morning. Submit the assignment before Monday. Also, review the presentation slides as soon as possible."

# ----------------------------------------------------------------------
# Auth & Export Helpers
# ----------------------------------------------------------------------
def login_screen():
    st.markdown('<div class="brand" style="justify-content:center; font-size:2rem; margin-top:50px;">✦ Talk2Task</div>', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center; color:var(--muted); margin-bottom:30px;">Sign in to manage your tasks</div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        st.markdown("<br>", unsafe_allow_html=True)
        user = st.text_input("Username", key="login_user")
        pwd = st.text_input("Password", type="password", key="login_pwd")
        if st.button("Sign In", type="primary", use_container_width=True):
            role = auth.login(user, pwd)
            if role:
                st.session_state.logged_in = True
                st.session_state.username = user
                st.session_state.role = role
                st.rerun()
            else:
                st.error("Invalid credentials")
                
    with tab2:
        st.markdown("<br>", unsafe_allow_html=True)
        new_user = st.text_input("Choose Username", key="reg_user")
        new_pwd = st.text_input("Choose Password", type="password", key="reg_pwd")
        if st.button("Create Account", use_container_width=True):
            if auth.register(new_user, new_pwd):
                st.success("Account created! Please log in.")
            else:
                st.error("Username already exists.")

def generate_ics(tasks):
    ics_lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Talk2Task//NLP//EN"]
    for t in tasks:
        if "No deadline" not in t.get("deadline", ""):
            uid = str(uuid.uuid4())
            dtstamp = datetime.now().strftime("%Y%m%dT%H%M%SZ")
            ics_lines.extend([
                "BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{dtstamp}",
                f"SUMMARY:{t['description']}",
                f"DESCRIPTION:Priority: {t['priority']}\\nSource: {t['original_sentence']}",
                "END:VEVENT"
            ])
    ics_lines.append("END:VCALENDAR")
    return "\n".join(ics_lines)

# ----------------------------------------------------------------------
# Task Rendering
# ----------------------------------------------------------------------
def render_task_item(t, idx, is_admin=False, prefix="dash"):
    with st.container(border=True):
        c_text, c_badge = st.columns([8, 2])
        with c_text:
            st.markdown(f"**{t['description']}**")
            st.markdown(f"<span style='color:var(--muted); font-size:0.85rem;'>📅 {t['deadline']} &nbsp;&nbsp; 🔑 {t['action_keyword']}</span>", unsafe_allow_html=True)
            if is_admin:
                st.markdown(f"<span style='color:var(--brand); font-size:0.75rem;'>👤 {t.get('owner')}</span>", unsafe_allow_html=True)
                
        with c_badge:
            if t.get("completed"):
                st.markdown('<div class="badge badge-done" style="text-align:center; margin-top:10px;">✓ DONE</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="badge" style="text-align:center; margin-top:10px;">{t.get("priority")} Priority</div>', unsafe_allow_html=True)
        
        if not is_admin:
            c1, c2, c3, c4 = st.columns([1.5, 1.5, 1.5, 5.5])
            
            with c1:
                if not t.get("completed"):
                    if st.button("✅ Done", key=f"{prefix}_done_{idx}", use_container_width=True):
                        tasks = auth.get_user_tasks(st.session_state.username)
                        tasks[idx]["completed"] = True
                        auth.save_user_tasks(st.session_state.username, tasks)
                        st.rerun()
                        
            with c2:
                if st.button("⚙️ Edit", key=f"{prefix}_edit_{idx}", use_container_width=True):
                    st.session_state[f"{prefix}_edit_toggle_{idx}"] = not st.session_state.get(f"{prefix}_edit_toggle_{idx}", False)
                    
            with c3:
                if st.button("🗑 Delete", key=f"{prefix}_del_{idx}", use_container_width=True):
                    tasks = auth.get_user_tasks(st.session_state.username)
                    tasks.pop(idx)
                    auth.save_user_tasks(st.session_state.username, tasks)
                    st.rerun()
                    
            if st.session_state.get(f"{prefix}_edit_toggle_{idx}", False):
                new_desc = st.text_input("Update description", value=t["description"], key=f"{prefix}_desc_input_{idx}")
                if new_desc.strip() != t["description"]:
                    tasks = auth.get_user_tasks(st.session_state.username)
                    tasks[idx]["description"] = new_desc.strip() or t["description"]
                    auth.save_user_tasks(st.session_state.username, tasks)

# ----------------------------------------------------------------------
# MAIN APP ROUTER
# ----------------------------------------------------------------------
if not st.session_state.logged_in:
    login_screen()
else:
    tasks = auth.get_user_tasks(st.session_state.username)
    
    # ------------------ SIDEBAR ------------------
    with st.sidebar:
        st.markdown(f'<div class="brand">✦ Talk2Task</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="brand-sub">Logged in as: <b>{st.session_state.username}</b> ({st.session_state.role})</div>', unsafe_allow_html=True)
        
        menu_options = ["Home Dashboard", "Extract New Tasks", "Focus Mode", "Eisenhower Matrix"]
        if st.session_state.role == "admin":
            menu_options.append("Admin Portal")
            
        selected = st.radio("Navigation", menu_options, index=menu_options.index(st.session_state.nav) if st.session_state.nav in menu_options else 0, label_visibility="collapsed")
        if selected != st.session_state.nav:
            st.session_state.nav = selected
            st.rerun()

        st.markdown("<br><hr style='border-color:#D6E4E1;'>", unsafe_allow_html=True)
        
        done = sum(1 for t in tasks if t.get("completed"))
        st.progress(done / len(tasks) if len(tasks) > 0 else 0)
        st.caption(f"{done} of {len(tasks)} tasks completed")
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.role = ""
            st.rerun()

    # ------------------ VIEWS ------------------
    
    if st.session_state.nav == "Admin Portal" and st.session_state.role == "admin":
        st.markdown('<div class="section-title">🛡️ Admin Portal</div>', unsafe_allow_html=True)
        all_tasks = auth.get_all_system_tasks()
        
        total_sys = len(all_tasks)
        users = set([t.get("owner") for t in all_tasks])
        
        st.markdown(f"""
            <div class="metrics" style="grid-template-columns: repeat(2, 1fr);">
                <div class="metric"><div class="value v-blue">{total_sys}</div><div class="label">Total System Tasks</div></div>
                <div class="metric"><div class="value v-green">{len(users)}</div><div class="label">Active Users</div></div>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="section-title">All System Tasks</div>', unsafe_allow_html=True)
        for i, t in enumerate(all_tasks):
            render_task_item(t, i, is_admin=True, prefix="admin")
            
    elif st.session_state.nav == "Home Dashboard":
        st.markdown("""<div class="hero"><h1>Welcome to Talk2Task</h1><p>Intelligent matching for your daily action items.</p></div>""", unsafe_allow_html=True)
        
        priority_order = {"High": 1, "Medium": 2, "Low": 3}
        tasks = sorted(tasks, key=lambda x: priority_order.get(x.get("priority", "Medium"), 2))

        total = len(tasks)
        done = sum(1 for t in tasks if t.get("completed"))
        high = sum(1 for t in tasks if t.get("priority") == "High")

        st.markdown(f"""
            <div class="metrics">
                <div class="metric"><div class="value v-blue">{total}</div><div class="label">Total Tasks</div></div>
                <div class="metric"><div class="value v-amber">{total - done}</div><div class="label">Pending</div></div>
                <div class="metric"><div class="value v-green">{done}</div><div class="label">Completed</div></div>
                <div class="metric"><div class="value v-red">{high}</div><div class="label">High Priority</div></div>
            </div>
        """, unsafe_allow_html=True)

        if total == 0:
            st.info("No tasks found. Go to 'Extract New Tasks' to get started!")
        else:
            col1, col2 = st.columns([1.8, 1])
            with col1:
                st.markdown('<div class="section-title">Action Items</div>', unsafe_allow_html=True)
                for i, t in enumerate(tasks[:6]):
                    render_task_item(t, i, prefix="dash")
                    
                # EXPORT BUTTONS
                st.markdown("---")
                st.markdown('<div class="section-title" style="font-size:1.1rem; margin-bottom:10px;">Export Data</div>', unsafe_allow_html=True)
                c_exp1, c_exp2 = st.columns(2)
                with c_exp1:
                    df = pd.DataFrame([{"Task": t["description"], "Deadline": t["deadline"], "Priority": t["priority"]} for t in tasks])
                    st.download_button("⬇️ Download CSV", data=df.to_csv(index=False).encode("utf-8"), file_name="talk2task.csv", mime="text/csv", use_container_width=True)
                with c_exp2:
                    ics_data = generate_ics(tasks)
                    if ics_data:
                        st.download_button("📅 Add to Calendar (.ics)", data=ics_data, file_name="talk2task_calendar.ics", mime="text/calendar", use_container_width=True)
                        
            with col2:
                st.markdown('<div class="section-title">Analytics</div>', unsafe_allow_html=True)
                
                df_chart = pd.DataFrame([t.get("priority") for t in tasks], columns=["Priority"])
                counts = df_chart["Priority"].value_counts().reset_index()
                color_scale = alt.Scale(domain=['High', 'Medium', 'Low'], range=['#D9534F', '#F0AD4E', '#5CB85C'])
                donut = alt.Chart(counts).mark_arc(innerRadius=50, outerRadius=80).encode(
                    theta=alt.Theta(field="count", type="quantitative"), 
                    color=alt.Color(field="Priority", type="nominal", scale=color_scale, legend=alt.Legend(orient="bottom", title=None))
                ).properties(height=220, background='transparent', title="Priority Distribution")
                
                df_status = pd.DataFrame({"Status": ["Completed" if t.get("completed") else "Pending" for t in tasks]})
                status_counts = df_status["Status"].value_counts().reset_index()
                status_chart = alt.Chart(status_counts).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
                    x=alt.X("Status", axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("count", title="Tasks"),
                    color=alt.Color("Status", scale=alt.Scale(domain=["Completed", "Pending"], range=["#5CB85C", "#F0AD4E"]), legend=None)
                ).properties(height=150, background='transparent', title="Task Status")
                
                st.altair_chart(donut, use_container_width=True)
                st.altair_chart(status_chart, use_container_width=True)

    elif st.session_state.nav == "Extract New Tasks":
        st.markdown('<div class="section-title">Extract Tasks from Text</div>', unsafe_allow_html=True)
        
        if st.button("✨ Use Sample"):
            st.session_state.raw_text = SAMPLE_TEXT
            st.rerun()

        text = st.text_area("Paste text", value=st.session_state.raw_text, height=200, label_visibility="collapsed")
        
        if st.button("Extract Tasks →", type="primary"):
            if text.strip():
                with st.spinner("Analyzing NLP pipeline..."):
                    try:
                        new_tasks, _ = extract_tasks(text)
                        if new_tasks:
                            tasks.extend(new_tasks)
                            auth.save_user_tasks(st.session_state.username, tasks)
                            st.session_state.raw_text = "" 
                            st.session_state.nav = "Home Dashboard"
                            st.rerun()
                        else:
                            st.info("No action items found. Try adding verbs like 'submit' or 'call'.")
                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                st.warning("Please paste some text first.")

    elif st.session_state.nav == "Focus Mode":
        st.markdown('<div class="section-title">🎯 Focus Mode</div>', unsafe_allow_html=True)
        pending = [(i, t) for i, t in enumerate(tasks) if not t.get("completed")]
        if not pending:
            st.success("🎉 All tasks completed!")
        else:
            idx, t = pending[st.session_state.focus_idx % len(pending)]
            st.markdown(f"**Task {st.session_state.focus_idx + 1} of {len(pending)}**")
            st.markdown(f"<div style='background:white; border:1px solid #D6E4E1; border-radius:12px; padding:50px; text-align:center;'><h2>{t['description']}</h2><p>📅 {t['deadline']}</p></div>", unsafe_allow_html=True)
            
            b1, b2, b3 = st.columns([1, 2, 1])
            with b1:
                if st.button("← Prev") and st.session_state.focus_idx > 0: 
                    st.session_state.focus_idx -= 1
                    st.rerun()
            with b2:
                if st.button("✓ Complete", type="primary"):
                    tasks[idx]["completed"] = True
                    auth.save_user_tasks(st.session_state.username, tasks)
                    st.rerun()

    elif st.session_state.nav == "Eisenhower Matrix":
        st.markdown('<div class="section-title">🎯 Eisenhower Matrix</div>', unsafe_allow_html=True)
        
        do_first = [t for t in tasks if t.get("priority") == "High" and "No deadline" not in t.get("deadline","") and not t.get("completed")]
        schedule = [t for t in tasks if t.get("priority") == "High" and "No deadline" in t.get("deadline","") and not t.get("completed")]
        delegate = [t for t in tasks if t.get("priority") in ["Medium", "Low"] and "No deadline" not in t.get("deadline","") and not t.get("completed")]
        dont_do = [t for t in tasks if t.get("priority") in ["Medium", "Low"] and "No deadline" in t.get("deadline","") and not t.get("completed")]

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🚨 DO FIRST")
            if not do_first: st.success("Clear!")
            for t in do_first: render_task_item(t, tasks.index(t), prefix="matrix_a")
            
            st.markdown("<br>### 📅 SCHEDULE")
            if not schedule: st.success("Clear!")
            for t in schedule: render_task_item(t, tasks.index(t), prefix="matrix_b")
            
        with col2:
            st.markdown("### 🤝 DELEGATE")
            if not delegate: st.success("Clear!")
            for t in delegate: render_task_item(t, tasks.index(t), prefix="matrix_c")
            
            st.markdown("<br>### 🗑️ DON'T DO")
            if not dont_do: st.success("Clear!")
            for t in dont_do: render_task_item(t, tasks.index(t), prefix="matrix_d")