import streamlit as st
import fitz, re, random

# ---------------- PDF parser (unchanged) ----------------
@st.cache_data
def load_questions(pdf):
    doc = fitz.open(pdf)
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

# ---------------- Streamlit UI ----------------
st.set_page_config("Luke Quiz", "📖")
st.title("📖 Luke Multiple‑Choice Bible Quiz")

PDF = "03_Luke_MC_Questions.pdf"
QUESTIONS = load_questions(PDF)
if not QUESTIONS:
    st.error("Could not parse questions — check the PDF path/format.")
    st.stop()

# Initialize session state
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

st.subheader("Question")
st.write(q["question"])

# Disable radio after submit
disabled_flag = st.session_state.answered
st.session_state.selection = st.radio(
    "Choose:",
    q["choices"],
    index=(q["choices"].index(st.session_state.selection)
           if st.session_state.selection in q["choices"] else 0),
    disabled=disabled_flag,
    key="radio",
)

# Submit button
if st.button("Submit", disabled=st.session_state.answered):
    if st.session_state.selection == q["correct"]:
        st.success("✅ Correct!")
    else:
        st.error("❌ Incorrect.")
        st.info(f"**Correct answer:** {q['correct']}")
    st.session_state.answered = True

# Next button (only after answering)
if st.session_state.answered:
    st.button("Next Question ▶️", on_click=new_question)

