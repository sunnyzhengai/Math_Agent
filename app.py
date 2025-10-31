
import streamlit as st
from engine import templates
from engine.grader import grade
from engine.state import load_user_state, save_user_state, ensure_skill, update_after_answer, mastered
from engine.planner import next_skill, generate_item_for_skill, generate_adaptive_item, lesson_for_tags, SKILL_LIST, reload_skills
from engine.neo4j_sync import Neo4jSync, sync_to_neo4j, log_attempt_to_neo4j
import time

st.set_page_config(page_title="Quadratics MVP", page_icon="🧮", layout="centered")

# Force reload skills on every app run (supports hot-reload of skills.json)
reload_skills()

st.title("🧮 Quadratics Mastery (MVP)")

QUESTIONS_PER_SKILL = 5  # ← MODIFY THIS to change number of questions per skill

with st.sidebar:
    st.header("Progress")
    username = st.text_input("Learner name", value="julia")
    if st.button("Reset Progress"):
        save_user_state(username, {"username": username, "skills": {}, "history": [], "questions_answered": 0})
        st.success("Progress reset.")
    
    # Show Neo4j dashboard if available
    try:
        sync = Neo4jSync()
        dashboard = sync.get_dashboard(username.lower())
        sync.close()
        
        if dashboard:
            st.divider()
            st.subheader("📊 Neo4j Dashboard")
            
            # Show stats
            col1, col2, col3 = st.columns(3)
            col1.metric("Mastered", f"{dashboard['stats']['mastered']}")
            col2.metric("Practicing", f"{dashboard['stats']['practicing']}")
            col3.metric("Struggling", f"{dashboard['stats']['struggling']}")
            
            st.metric("Average Mastery", f"{dashboard['stats']['avg_mastery']:.0%}")
    except Exception as e:
        # Neo4j not available - continue without it
        pass

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

# Show Neo4j recommendation if available
try:
    sync = Neo4jSync()
    recommendation = sync.get_next_skill_recommendation(username.lower())
    sync.close()
    
    if recommendation:
        st.info(f"🎯 **Next Recommended Skill:** {recommendation['skill_name']}\n\n{recommendation['rationale']}")
except Exception as e:
    # Neo4j not available
    pass

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
            item = generate_adaptive_item(sid, state)
            st.session_state.current_item = item
            st.session_state.feedback = None

    with col2:
        if st.button("📊 Show Skill List"):
            st.session_state.current_item = None
            st.session_state.feedback = None

    if st.session_state.current_item:
        item = st.session_state.current_item
        st.subheader(item["stem"])
        
        # Show adaptive difficulty and mastery level (for transparency)
        if "adaptive_difficulty" in item:
            col_diff, col_mastery = st.columns([1, 2])
            with col_diff:
                difficulty_emoji = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}.get(item["adaptive_difficulty"], "❓")
                st.caption(f"{difficulty_emoji} {item['adaptive_difficulty'].upper()}")
            with col_mastery:
                mastery_pct = int(item.get("learner_mastery", 0.6) * 100)
                st.caption(f"📈 Mastery: {mastery_pct}%")
        
        options = {c["id"]: c["text"] for c in item["choices"]}
        choice = st.radio("Choose one:", list(options.keys()), format_func=lambda k: options[k])

        if st.button("Submit"):
            # Track time for analytics
            attempt_start = time.time()
            
            result = grade(item, choice)
            correct, tags, chosen_text, score = result
            update_after_answer(state, item["skill_id"], correct, tags)
            
            # Increment questions answered
            state["questions_answered"] = questions_answered + 1
            save_user_state(username, state)
            
            # Reload state to show updated mastery immediately
            state = load_user_state(username)
            
            # Calculate time spent
            time_ms = int((time.time() - attempt_start) * 1000)
            
            # Log attempt to Neo4j (immutable record)
            try:
                attempt_log = log_attempt_to_neo4j(
                    user=username.lower(),
                    skill_id=item["skill_id"],
                    item_id=item["id"],
                    correct=correct,
                    tags=tags,
                    time_ms=time_ms
                )
                # Store attempt_id in session for reference
                st.session_state.last_attempt_id = attempt_log.get("attempt_id")
            except Exception as e:
                # Log failed, continue
                pass
            
            # Sync to Neo4j in real-time
            try:
                neo_result = sync_to_neo4j(
                    user=username.lower(),
                    skill_id=item["skill_id"],
                    correct=correct,
                    tags=tags
                )
                
                # Show remediation mini-lesson if triggered
                if neo_result.get("remediation"):
                    rem = neo_result["remediation"]
                    st.warning(f"📚 Remediation Triggered: {rem['misconception_name']}")
                    st.write(f"**{rem['lesson_title']}**")
                    st.write(rem['lesson_content'])
                    
                # Show updated Neo4j progress
                prog = neo_result["progress"]
                st.metric(
                    "Neo4j Mastery",
                    f"{prog['p_mastery']:.0%}",
                    f"{prog['seen']} attempts, {prog['streak']} streak"
                )
            except Exception as e:
                # Neo4j sync failed, but continue with local progress
                pass

            # build feedback
            if correct:
                icon = "✅ Correct! (Full credit)"
            elif score > 0:
                icon = f"⚠️ Partial credit ({int(score*100)}%)"
            else:
                icon = "❌ Not quite. (No credit)"
            lessons = lesson_for_tags(tags)
            st.session_state.feedback = (icon, tags, lessons, item)
            
            # Show updated mastery immediately
            skill_state = state["skills"].get(item["skill_id"], {})
            new_mastery = skill_state.get("p_mastery", 0.6)
            st.success(f"📈 **Mastery updated: {new_mastery:.0%}**")

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
