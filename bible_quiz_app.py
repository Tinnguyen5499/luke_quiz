import streamlit as st
import fitz                                # PyMuPDF
import re, random, pandas as pd

# ────────────────────────── Helper: universal rerun ──────────────────────────
def _do_rerun():
    """Call st.rerun() on all Streamlit versions."""
    if hasattr(st, "rerun"):                      # Streamlit ≥ 1.26
        st.rerun()
    elif hasattr(st, "experimental_rerun"):       # Older versions
        st.experimental_rerun()

# ────────── Universal singleton decorator (works on any Streamlit) ───────────
if hasattr(st, "singleton"):                      # Streamlit ≥ 1.18
    singleton = st.singleton
elif hasattr(st, "experimental_singleton"):       # Older versions
    singleton = st.experimental_singleton
else:                                             # Very new versions
    singleton = st.cache_resource

@singleton
def leaderboard():
    """Shared dict {player: {'correct': int, 'attempted': int}}."""
    return {}

def update_score(player: str, correct: bool):
    board = leaderboard()
    if player not in board:
        board[player] = {'correct': 0, 'attempted': 0}
    board[player]['attempted'] += 1
    if correct:
        board[player]['correct'] += 1

# ──────────────────────── PDF parser (unchanged) ─────────────────────────────
@st.cache_data
def load_questions(pdf_path: str):
    doc = fitz.open(pdf_path)
    raw = [ln.rstrip() for pg in doc for ln in pg.get_text().splitlines()]

    qs, i = [], 0
    while i < len(raw):
        m_q = re.match(r"^(\d{1,3})\.\s+(.*)", raw[i].strip())
        if not m_q:
            i += 1
            continue

        q_parts, i = [m_q.group(2)], i + 1
        while i < len(raw) and not re.match(r"^A\.\s*$", raw[i].strip()):
            if raw[i].strip() and not re.match(r"^\d+\s*$", raw[i].strip()):
                q_parts.append(raw[i].strip())
            i += 1

        choices, correct_letter = {}, None
        for opt in "ABCD":
            if i < len(raw) and re.match(fr"^{opt}\.\s*$", raw[i].strip()):
                i += 1
                c_parts = []
                while (i < len(raw)
                       and not re.match(r"^[A-D]\.\s*$", raw[i].strip())
                       and not re.match(r"^[A-D]:[BIA]:Lk:", raw[i].strip())):
                    if raw[i].strip():
                        c_parts.append(raw[i].strip())
                    i += 1
                choices[opt] = f"{opt}. {' '.join(c_parts)}"

        if i < len(raw):
            m_ans = re.match(r"^([A-D]):[BIA]:Lk:", raw[i].strip())
            if m_ans:
                correct_letter, i = m_ans.group(1), i + 1

        if correct_letter and len(choices) == 4:
            qs.append(
                dict(
                    question=" ".join(q_parts),
                    choices=[choices[k] for k in "ABCD"],
                    correct=choices[correct_letter],
                )
            )
    return qs

# ──────────────────────────── Streamlit UI ───────────────────────────────────
st.set_page_config("Luke Quiz", "📖", layout="centered")
st.title("📖 Luke Multiple‑Choice Bible Quiz")

QUESTIONS = load_questions("03_Luke_MC_Questions.pdf")
if not QUESTIONS:
    st.error("Could not parse questions — check PDF location.")
    st.stop()

# 1️⃣  Ask for player name (main page)
if "player_name" not in st.session_state:
    st.subheader("Enter your name to start")
    name = st.text_input("Name")
    if st.button("Start ▶️") and name.strip():
        st.session_state.player_name = name.strip()
        _do_rerun()
    st.stop()

player = st.session_state.player_name

# 2️⃣  Initialize per‑session quiz state
if "q_idx" not in st.session_state:
    st.session_state.q_idx = random.randrange(len(QUESTIONS))
if "answered" not in st.session_state:
    st.session_state.answered = False
if "selection" not in st.session_state:
    st.session_state.selection = None

def new_question():
    st.session_state.q_idx = random.randrange(len(QUESTIONS))
    st.session_state.answered = False
    st.session_state.selection = None

q = QUESTIONS[st.session_state.q_idx]

# 3️⃣  Show personal running score
stats = leaderboard().get(player, {'correct': 0, 'attempted': 0})
attempts, corr = stats['attempted'], stats['correct']
percent = f"{corr/attempts*100:.1f}%" if attempts else "‑"
st.markdown(f"**{player} — Score:** {corr}/{attempts} &nbsp;&nbsp;|&nbsp;&nbsp; **Accuracy:** {percent}")

# 4️⃣  Display question and choices
st.subheader("Question")
st.write(q["question"])

st.session_state.selection = st.radio(
    "Choose your answer:",
    q["choices"],
    index=(
        q["choices"].index(st.session_state.selection)
        if st.session_state.selection in q["choices"] else 0
    ),
    disabled=st.session_state.answered,
)

# 5️⃣  Submit button
if st.button("Submit", disabled=st.session_state.answered):
    is_correct = st.session_state.selection == q["correct"]
    if is_correct:
        st.success("✅ Correct!")
    else:
        st.error("❌ Incorrect.")
        st.info(f"**Correct answer:** {q['correct']}")
    update_score(player, is_correct)
    st.session_state.answered = True
    _do_rerun()

# 6️⃣  Next Question button
if st.session_state.answered:
    st.button("Next Question ▶️", on_click=new_question)

# 7️⃣  Leaderboard in sidebar
st.sidebar.header("🏆 Leaderboard")
if leaderboard():
    df = (
        pd.DataFrame(leaderboard())
        .T.rename(columns={'correct': 'Correct', 'attempted': 'Attempts'})
        .assign(Percent=lambda d: (d['Correct'] / d['Attempts'] * 100).round(1))
        .sort_values(['Percent', 'Attempts'], ascending=[False, False])
    )
    st.sidebar.dataframe(df, use_container_width=True)
else:
    st.sidebar.write("No scores yet — be the first!")
