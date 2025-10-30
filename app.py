
import streamlit as st
from engine import templates
from engine.grader import grade
from engine.state import load_user_state, save_user_state, ensure_skill, update_after_answer, mastered
from engine.planner import next_skill, generate_item_for_skill, lesson_for_tags, SKILL_LIST

st.set_page_config(page_title="Quadratics MVP", page_icon="🧮", layout="centered")

st.title("🧮 Quadratics Mastery (MVP)")

QUESTIONS_PER_SKILL = 5  # ← MODIFY THIS to change number of questions per skill

with st.sidebar:
    st.header("Progress")
    username = st.text_input("Learner name", value="julia")
    if st.button("Reset Progress"):
        save_user_state(username, {"username": username, "skills": {}, "history": [], "questions_answered": 0})
        st.success("Progress reset.")

state = load_user_state(username)

# Calculate total questions and progress
total_skills = len(SKILL_LIST)
total_questions = total_skills * QUESTIONS_PER_SKILL
questions_answered = state.get("questions_answered", 0)

# Show progress summary
with st.sidebar:
    st.metric("Progress", f"{questions_answered}/{total_questions}", f"{(questions_answered/total_questions)*100:.0f}%")
    
    if state.get("skills"):
        st.subheader("Skill Progress")
        for s in SKILL_LIST:
            sid = s["id"]
            stt = state["skills"].get(sid)
            if stt:
                label = "✅ Mastered" if mastered(state, sid) else "📘 Practicing"
                st.progress(min(1.0, stt["p_mastery"]), text=f"{s['name']} — {label} ({stt['p_mastery']:.2f})")
    else:
        st.info("No progress yet. Start practicing to see your mastery.")

if "current_item" not in st.session_state:
    st.session_state.current_item = None
if "current_skill" not in st.session_state:
    st.session_state.current_skill = None
if "feedback" not in st.session_state:
    st.session_state.feedback = None

# Check if quiz is complete
if questions_answered >= total_questions:
    st.success("🎉 Congratulations! You've completed all questions!")
    if st.button("Reset Progress and Start Over"):
        save_user_state(username, {"username": username, "skills": {}, "history": [], "questions_answered": 0})
        st.rerun()
else:
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎯 Get Next Question"):
            sid = next_skill(state)
            st.session_state.current_skill = sid
            item = generate_item_for_skill(sid, difficulty="med")
            st.session_state.current_item = item
            st.session_state.feedback = None

    with col2:
        if st.button("📊 Show Skill List"):
            st.session_state.current_item = None
            st.session_state.feedback = None

    if st.session_state.current_item:
        item = st.session_state.current_item
        st.subheader(item["stem"])
        
        
        options = {c["id"]: c["text"] for c in item["choices"]}
        choice = st.radio("Choose one:", list(options.keys()), format_func=lambda k: options[k])

        if st.button("Submit"):
            result = grade(item, choice)
            correct, tags, chosen_text, score = result
            update_after_answer(state, item["skill_id"], correct, tags)
            
            # Increment questions answered
            state["questions_answered"] = questions_answered + 1
            save_user_state(username, state)

            # build feedback
            if correct:
                icon = "✅ Correct! (Full credit)"
            elif score > 0:
                icon = f"⚠️ Partial credit ({int(score*100)}%)"
            else:
                icon = "❌ Not quite. (No credit)"
            lessons = lesson_for_tags(tags)
            st.session_state.feedback = (icon, tags, lessons, item)

        if st.session_state.feedback:
            icon, tags, lessons, item = st.session_state.feedback
            st.markdown(f"**{icon}**")
            st.markdown(f"**Answer:** {item['solution']}")
            st.caption(item.get("rationale",""))
            if tags:
                st.write("Detected:", ", ".join(tags))
            if lessons:
                with st.expander("Mini-lesson"):
                    for t, txt in lessons:
                        st.markdown(f"**{t}** — {txt}")

    else:
        st.subheader("Skills in this MVP")
        for s in SKILL_LIST:
            st.write(f"- **{s['name']}** (`{s['id']}`)")
        st.info("Click **🎯 Get Next Question** to begin.")
