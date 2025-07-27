import streamlit as st, fitz, re, random, pandas as pd, glob, os

# ─────────── universal rerun helper ───────────
def _rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()

# ─────────── universal singleton decorator ────
if hasattr(st, "singleton"):
    singleton = st.singleton
elif hasattr(st, "experimental_singleton"):
    singleton = st.experimental_singleton
else:
    singleton = st.cache_resource

@singleton
def leaderboard():
    return {}    # {quiz_id: {player: {'correct':int,'attempted':int}}}

def update_score(quiz_id, player, correct):
    board = leaderboard().setdefault(quiz_id, {})
    stats = board.setdefault(player, {'correct': 0, 'attempted': 0})
    stats['attempted'] += 1
    if correct:
        stats['correct'] += 1

# ─────────────────── PDF → questions ──────────────────
@st.cache_data
def parse_pdf(path: str):
    doc = fitz.open(path)
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
                       and not re.match(r"^[A-D]:[BIA]:\w\w:", raw[i].strip())):
                    if raw[i].strip():
                        c_parts.append(raw[i].strip())
                    i += 1
                choices[opt] = f"{opt}. {' '.join(c_parts)}"
        if i < len(raw):
            m_ans = re.match(r"^([A-D]):[BIA]:\w\w:", raw[i].strip())
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
    random.shuffle(qs)
    return qs

# ──────────────── load every *_MC_Questions.pdf ────────────────
@st.cache_data
def load_all_quizzes():
    quizzes = {}
    for path in glob.glob("*_MC_Questions.pdf"):
        book = re.search(r"_([A-Za-z]+)_MC_Questions\.pdf", path).group(1).title()
        quizzes[book] = parse_pdf(path)
    # combined “All Books” list
    if len(quizzes) >= 2:
        all_qs = sum(quizzes.values(), [])  # concatenate lists
        random.shuffle(all_qs)
        quizzes["All Books"] = all_qs
    return quizzes

QUIZZES = load_all_quizzes()
if not QUIZZES:
    st.error("No *_MC_Questions.pdf files in folder.")
    st.stop()

# ─────────────── Streamlit UI ─────────────────────────
st.set_page_config("Bible Quiz", "📖", layout="centered")
st.title("📖 Bible Multiple‑Choice Quiz")

# Book selector
if "book" not in st.session_state:
    st.session_state.book = list(QUIZZES.keys())[0]

st.session_state.book = st.selectbox(
    "Choose a quiz set:", list(QUIZZES.keys()),
    index=list(QUIZZES.keys()).index(st.session_state.book)
)
quiz_id = st.session_state.book
QUESTIONS = QUIZZES[quiz_id]

# Name prompt
if "player" not in st.session_state:
    st.subheader("Enter your name to start")
    name = st.text_input("Name")
    if st.button("Start ▶️") and name.strip():
        st.session_state.player = name.strip()
        st.session_state.idx = 0
        st.session_state.correct = 0
        _rerun()
    st.stop()

player = st.session_state.player

# Reset progress if player switches quiz
if "current_quiz" not in st.session_state or st.session_state.current_quiz != quiz_id:
    st.session_state.current_quiz = quiz_id
    st.session_state.idx = 0
    st.session_state.correct = 0

idx = st.session_state.idx

# Personal score line
attempts = idx
correct = st.session_state.correct
pct = f"{correct/attempts*100:.1f}%" if attempts else "‑"
st.markdown(f"**{player} — {quiz_id} score:** {correct}/{attempts}  |  **Accuracy:** {pct}")

# Show question / flow
if idx < len(QUESTIONS):
    q = QUESTIONS[idx]
    st.subheader(f"Question {idx+1} / {len(QUESTIONS)}")
    choice = st.radio(q["question"], q["choices"], index=None, key=idx)
    if st.button("Submit", key=f"sub{idx}") and choice:
        is_correct = choice == q["correct"]
        if is_correct:
            st.success("✅ Correct!")
            st.session_state.correct += 1
        else:
            st.error("❌ Incorrect.")
            st.info(f"**Correct answer:** {q['correct']}")
        update_score(quiz_id, player, is_correct)
        st.session_state.idx += 1
        _rerun()
else:
    st.balloons()
    st.success(f"Finished {quiz_id}! Final: {correct}/{attempts} ({pct})")
    if st.button("Restart this quiz"):
        st.session_state.idx = 0
        st.session_state.correct = 0
        _rerun()

# Leaderboard
st.sidebar.header("🏆 Leaderboard")
lb = leaderboard().get(quiz_id, {})
if lb:
    df = (pd.DataFrame(lb)
          .T.rename(columns={'correct':'Correct','attempted':'Attempts'})
          .assign(Percent=lambda d:(d['Correct']/d['Attempts']*100).round(1))
          .sort_values(['Percent','Attempts'], ascending=[False, False]))
    st.sidebar.markdown(f"### {quiz_id}")
    st.sidebar.dataframe(df, use_container_width=True)
else:
    st.sidebar.write("No scores yet for this quiz.")
