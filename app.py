"""
Streamlit UI for the Agent Pipeline.
Run with:  streamlit run app.py
"""

import html

import streamlit as st
from dotenv import load_dotenv

# Load .env BEFORE importing our modules, because they read settings
# (provider, model, throttle) from environment variables at import time.
load_dotenv()

from mistral_client import DEFAULT_MODEL, PROVIDER  # noqa: E402
from orchestator import make_plan, run_step, synthesize  # noqa: E402

st.set_page_config(
    page_title="Agent Pipeline",
    page_icon="🤖",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------- styling
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Space Grotesk', sans-serif;
}

/* vibrant animated-looking background */
.stApp {
    background:
        radial-gradient(circle at 10% 8%,  rgba(255, 64, 160, 0.35) 0%, transparent 38%),
        radial-gradient(circle at 90% 15%, rgba(0, 200, 255, 0.30) 0%, transparent 40%),
        radial-gradient(circle at 50% 95%, rgba(140, 80, 255, 0.35) 0%, transparent 45%),
        #0a0a1c;
    color: #f2f2ff;
}

/* remove sidebar, its toggle arrow, and default chrome */
[data-testid="stSidebar"],
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] { display: none !important; }
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }

.block-container { max-width: 820px; padding-top: 2.5rem; }

/* hero */
.pills { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px; }
.pill {
    font-size: 11px; letter-spacing: 0.14em; font-weight: 700;
    padding: 5px 12px; border-radius: 999px; color: #0a0a1c;
}
.pill:nth-child(1) { background: #ff5fc8; }
.pill:nth-child(2) { background: #ffb347; }
.pill:nth-child(3) { background: #5ff0a8; }
.pill:nth-child(4) { background: #5fd4ff; }

.hero-title {
    font-size: 3rem; font-weight: 700; line-height: 1.1; margin: 0 0 8px 0;
    background: linear-gradient(90deg, #ff5fc8, #ffb347 35%, #5ff0a8 65%, #5fd4ff);
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent; color: transparent;
}
.hero-sub { color: #c9c9ee; font-size: 1.02rem; margin-bottom: 26px; }

/* input */
.stTextArea textarea {
    background: rgba(20, 20, 50, 0.75) !important;
    color: #f2f2ff !important;
    border: 1.5px solid rgba(255, 95, 200, 0.55) !important;
    border-radius: 16px !important;
    font-size: 1rem !important;
    box-shadow: 0 0 22px rgba(255, 95, 200, 0.18);
}
.stTextArea textarea:focus {
    border-color: #5fd4ff !important;
    box-shadow: 0 0 26px rgba(95, 212, 255, 0.35) !important;
}
.stTextArea label p { color: #e6e6ff !important; font-weight: 500; }

/* button */
.stButton > button {
    background: linear-gradient(90deg, #ff4ecd, #8a5cff, #00c8ff) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 999px !important;
    padding: 0.65rem 2.2rem !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    box-shadow: 0 6px 26px rgba(138, 92, 255, 0.55);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.stButton > button:hover {
    transform: translateY(-2px) scale(1.03);
    box-shadow: 0 10px 34px rgba(255, 78, 205, 0.6);
}

/* section headings */
.section {
    font-size: 1.25rem; font-weight: 700; margin: 30px 0 12px 0;
    padding-left: 12px; border-left: 5px solid #ff5fc8; color: #ffffff;
}

/* plan cards */
.plan-card {
    display: flex; gap: 14px; align-items: flex-start;
    background: rgba(24, 24, 60, 0.72);
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 16px; padding: 14px 16px; margin-bottom: 10px;
    backdrop-filter: blur(6px);
}
.plan-num {
    min-width: 36px; height: 36px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; color: #0a0a1c;
    background: linear-gradient(135deg, #ffb347, #ff5fc8);
}
.plan-title { font-weight: 700; color: #ffffff; }
.plan-role  { color: #5fd4ff; font-size: 0.9rem; }

/* step expanders + final answer container */
div[data-testid="stExpander"], div[data-testid="stStatus"] {
    background: rgba(24, 24, 60, 0.72) !important;
    border: 1px solid rgba(95, 212, 255, 0.35) !important;
    border-radius: 14px !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 18px;
}
.final-box {
    background: linear-gradient(135deg, rgba(255,95,200,0.16), rgba(95,212,255,0.16));
    border: 1.5px solid rgba(95, 240, 168, 0.55);
    border-radius: 18px; padding: 6px 22px 14px 22px;
    box-shadow: 0 0 30px rgba(95, 240, 168, 0.18);
}

.footer-note { color: #8f8fc0; font-size: 0.78rem; margin-top: 40px; }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- header
st.markdown(
    """
<div class="pills">
  <span class="pill">PLAN</span>
  <span class="pill">SPAWN</span>
  <span class="pill">EXECUTE</span>
  <span class="pill">MERGE</span>
</div>
<div class="hero-title">Agent Pipeline</div>
<div class="hero-sub">Describe what you need. A planning agent splits it into steps,
a specialist agent handles each one, and everything is merged into one final answer.</div>
""",
    unsafe_allow_html=True,
)

# model comes straight from the active provider (no sidebar needed)
model = DEFAULT_MODEL

# ---------------------------------------------------------------- input
user_input = st.text_area(
    "Your request",
    placeholder="Example: Plan a 4-day Goa trip from Lucknow under 1 lakh",
    height=120,
)

run = st.button("🚀 Run pipeline", type="primary")

# ---------------------------------------------------------------- run
if run:

    if user_input.strip() == "":
        st.warning("Please enter a request first.")
    else:
        try:
            # step 1: plan
            with st.spinner("Planning..."):
                steps = make_plan(user_input, model)

            st.markdown('<div class="section">📋 Plan</div>', unsafe_allow_html=True)
            for step in steps:
                st.markdown(
                    '<div class="plan-card">'
                    '<div class="plan-num">' + str(step["id"]) + "</div>"
                    "<div>"
                    '<div class="plan-title">' + html.escape(str(step["title"])) + "</div>"
                    '<div class="plan-role">' + html.escape(str(step["agent_role"])) + "</div>"
                    "</div></div>",
                    unsafe_allow_html=True,
                )

            # step 2: run every step one by one
            st.markdown('<div class="section">⚙️ Step outputs</div>', unsafe_allow_html=True)
            results = []

            for step in steps:
                label = "Step " + str(step["id"]) + ": " + step["title"]
                with st.status(label, expanded=False) as status:
                    output = run_step(step, user_input, results, model)
                    results.append({"step": step, "output": output})
                    st.markdown(output)
                    status.update(label=label + " ✅", state="complete")

            # step 3: final answer
            with st.spinner("Creating final answer..."):
                final_answer = synthesize(user_input, results, model)

            st.markdown('<div class="section">✅ Final answer</div>', unsafe_allow_html=True)
            st.markdown('<div class="final-box">', unsafe_allow_html=True)
            st.markdown(final_answer)
            st.markdown("</div>", unsafe_allow_html=True)

        except Exception as e:
            st.error("Something went wrong: " + str(e))

st.markdown(
    '<div class="footer-note">' + html.escape(PROVIDER) + " · " + html.escape(model)
    + " · ephemeral agents, one plan at a time</div>",
    unsafe_allow_html=True,
)