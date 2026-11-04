import json
from collections import Counter

import streamlit as st
from google import genai
from google.genai import types

st.set_page_config(page_title="Msheireb Companion", page_icon="🌴")

# ---------- Setup ----------
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
MODEL = st.secrets.get("GEMINI_MODEL", "gemini-3.5-flash")

with open("data.json", encoding="utf-8") as f:
    PLACES = json.load(f)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "questions" not in st.session_state:
    st.session_state.questions = []

# ---------- Sidebar: live context + insights for Msheireb ----------
with st.sidebar:
    st.header("Live context")
    temp = st.slider("Temperature now (°C)", 20, 48, 38)
    time_of_day = st.selectbox("Time of day", ["Morning", "Afternoon", "Evening", "Late night"])

    st.divider()
    st.header("Msheireb insights (demo)")
    st.caption("What visitors asked for in this session")
    if st.session_state.questions:
        counts = Counter(st.session_state.questions)
        for topic, n in counts.most_common():
            st.write(f"- {topic}: {n}")
    else:
        st.write("No questions yet.")

# ---------- Prompt ----------
SYSTEM = f"""You are Msheireb Companion, a friendly assistant for visitors to Msheireb Downtown Doha.
Language rules:
- If the visitor writes in Arabic (any dialect: Levantine, Egyptian, Gulf, MSA...), ALWAYS reply in warm Qatari / Gulf dialect, never Modern Standard Arabic.
  Example: visitor "مرحبا انا ما بعرف وين روح وعندي بس ساعة اشرب فيها قهوة" -> you start like "هلا والله، نورت مشيرب! تبي تتقهوى؟ أبشر..." and adapt gender if the visitor's words show it (e.g. "نورتي، تبين تتقهوين؟ أبشري").
- If the visitor writes in any other language (English, French, Hindi, Urdu, Chinese, Turkish...), reply in that same language.
- Place names in the list are in Arabic. When replying in another language, write the place name in that language (translate or transliterate) followed by the Arabic name in brackets, e.g. "Arabica (أرابيكا)".
Only recommend places from this list; never invent places, prices or opening hours:
{json.dumps(PLACES, ensure_ascii=False)}

Current temperature: {temp}°C. Time of day: {time_of_day}.
Rules:
- Give 2-3 short suggestions that match the visitor's mood, need and the time.
- If the temperature is 35°C or above, prefer indoor or shaded places and suggest the tram or metro instead of long walks.
- Keep answers short and warm. Write the whole reply in one language (no English words inside an Arabic reply).
- Always write numbers with Western digits 0-9, also in Arabic replies (e.g. "38 درجة"). Never use Arabic-Indic digits like ٣٨.
- At the very end, on its own line, write: TOPIC: <one or two English words describing what the visitor wanted, e.g. coffee, kids activity, vegetarian food, museum>.
- If nothing in the list fits, say so honestly and still write the TOPIC line with 'unmet: ' before it."""

# ---------- Chat ----------
st.title("🌴 Msheireb Companion")
st.caption("Tell me your mood or what you need, and I'll suggest something nearby.")

def show(text):
    # dir="auto" lets the browser pick right-to-left for Arabic and left-to-right for English.
    # The blank lines keep markdown (bold, lists) working inside the HTML wrapper.
    st.markdown(f'<div dir="auto">\n\n{text}\n\n</div>', unsafe_allow_html=True)


for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        show(m["content"])

if prompt := st.chat_input("e.g. I'm bored and want a quiet coffee"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        show(prompt)

    history = [
        types.Content(role="user" if m["role"] == "user" else "model",
                      parts=[types.Part(text=m["content"])])
        for m in st.session_state.messages
    ]

    with st.spinner("Thinking..."):
        text = ""
        # Try the main model first. If it is busy (503) or out of free quota (429), fall back to the next one.
        # Free-tier quotas are per model, so each fallback adds more free requests per day.
        for model_name in dict.fromkeys([MODEL, "gemini-3.5-flash", "gemini-3.7-flash", "gemini-3.8-flash",
                                         "gemini-flash-latest", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite",
                                         "gemini-flash-lite-latest"]):
            try:
                resp = client.models.generate_content(
                    model=model_name,
                    contents=history,
                    config=types.GenerateContentConfig(system_instruction=SYSTEM, temperature=0.3),
                )
                text = resp.text or ""
                if text:
                    break
            except Exception as e:
                print(f"Gemini error ({model_name}):", str(e)[:200])
        if not text:
            text = "Sorry, I could not answer just now. Please try again in a moment. / عذراً، حاول مرة ثانية بعد لحظة."

    # Pull the TOPIC line out for the insights panel
    answer_lines, topic = [], None
    for line in text.splitlines():
        if line.strip().strip("*").upper().startswith("TOPIC:"):
            topic = line.split(":", 1)[1].strip().strip("*").strip()
        else:
            answer_lines.append(line)
    answer = "\n".join(answer_lines).strip()

    # The answer is drawn once, by the chat history loop above, after the rerun.
    st.session_state.messages.append({"role": "assistant", "content": answer})
    if topic:
        st.session_state.questions.append(topic)
    st.rerun()
