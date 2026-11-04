import json
from collections import Counter
from urllib.parse import quote_plus

import streamlit as st
from google import genai
from google.genai import types

st.set_page_config(page_title="Msheireb Companion", page_icon="🌴")

# ---------- Setup ----------
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
MODEL = st.secrets.get("GEMINI_MODEL", "gemini-3.5-flash")

with open("data.json", encoding="utf-8") as f:
    PLACES = json.load(f)
PLACE_BY_NAME = {p["name"]: p for p in PLACES}

# Ground-floor map areas (images in maps/). Places in data.json carry an "area" key when known.
AREAS = {
    "barahat": {"title": "Barahat Msheireb & Al Kahraba", "ar": "براحة مشيرب والكهرباء",
                "map": "maps/barahat-kahraba.png", "b1": "maps/b1-barahat.png"},
    "wadi": {"title": "Wadi Msheireb & Doha Design District", "ar": "وادي مشيرب وحي الدوحة للتصميم",
             "map": "maps/wadi-design-district.png", "b1": "maps/b1-wadi.png"},
    "heritage": {"title": "Heritage Quarter & M7", "ar": "الحي التراثي و M7",
                 "map": "maps/heritage-quarter.png", "b1": None},
    "galleria": {"title": "Msheireb Galleria", "ar": "مشيرب غاليريا",
                 "map": "maps/galleria.png", "b1": "maps/b1-galleria.png"},
}

# What the parking maps (basement B1) show. Lift-core names are not readable yet, so no lift-by-lift routes.
PARKING_INFO = """Parking basement B1 (colour zones on the parking signs and maps):
- Olive = Public (visitors), purple = Commercial, gold = VIP, teal = Residential, grey-brown = Others (staff, tenants).
- Main public visitor parking on B1: the large olive zone under the Galleria side (between the Museum Staff / Mosque parking and Virgin Active), and the olive zone on the Wadi side near Suhail Holding and Park Hyatt Doha.
- Commercial parking (purple) is next to Virgin Active, on the Galleria side.
- The Barahat side of B1 (under Qatar Academy, Mandarin Oriental, QMA) is mostly residential, VIP and staff parking.
- Ramps marked "UL0" go up to street level; ramps marked "B2" go down to level B2.
- To reach any shop or restaurant from the parking, take the nearest lift up to the ground floor (G)."""
NO_DIRECTIONS_TYPES = {"transport", "parking"}


def directions_url(name):
    return ("https://www.google.com/maps/dir/?api=1&travelmode=walking&destination="
            + quote_plus(f"{name} Msheireb Downtown Doha"))


def match_place(raw):
    """Map a name the model wrote to a real place in data.json (exact first, then containment)."""
    raw = raw.strip().strip("*").strip()
    if raw in PLACE_BY_NAME:
        return raw
    for name in PLACE_BY_NAME:
        if len(raw) >= 3 and (raw in name or name in raw):
            return name
    return None

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
- Some places have an "area" (barahat = Barahat Msheireb & Al Kahraba, wadi = Wadi Msheireb & Doha Design District, heritage = Heritage Quarter & M7, galleria = Msheireb Galleria). Mention the area briefly when you suggest such a place. Never invent step-by-step walking directions; a map and directions link are shown automatically below your reply.
{PARKING_INFO}
Lost visitors and wayfinding:
- If the visitor is lost, in the parking, or asks how to get somewhere: if you don't know where they are, ask ONE short question about what they can see right now (a shop, café, square, hotel or sign).
- Once you know a nearby place, tell them which area they are in and which area the destination is in, and that the maps are shown below. Give simple, honest guidance only (e.g. "take the lift up to the ground floor, you'll be in the Galleria area"). Never invent turn-by-turn routes, lift numbers or distances.
- Include BOTH the place they are next to and the destination in the PLACES line, so both maps are shown.
- Near the end, on its own line, write: PLACES: <the exact names, copied from the list, of the places you suggested, separated by |>, or PLACES: none.
- At the very end, on its own line, write: TOPIC: <one or two English words describing what the visitor wanted, e.g. coffee, kids activity, vegetarian food, museum>.
- If nothing in the list fits, say so honestly and still write the TOPIC line with 'unmet: ' before it."""

# ---------- Chat ----------
st.title("🌴 Msheireb Companion")
st.caption("Tell me your mood or what you need, and I'll suggest something nearby.")

def show(text):
    # dir="auto" lets the browser pick right-to-left for Arabic and left-to-right for English.
    # The blank lines keep markdown (bold, lists) working inside the HTML wrapper.
    st.markdown(f'<div dir="auto">\n\n{text}\n\n</div>', unsafe_allow_html=True)


def show_places(names):
    """Directions links for the suggested places, plus the ground-floor map of their area."""
    linkable = [n for n in names if PLACE_BY_NAME[n].get("type") not in NO_DIRECTIONS_TYPES]
    if linkable:
        links = " · ".join(f"[{n}]({directions_url(n)})" for n in linkable)
        show(f"📍 **Directions:** {links}")
    for area in dict.fromkeys(PLACE_BY_NAME[n]["area"] for n in names if "area" in PLACE_BY_NAME[n]):
        here = "، ".join(n for n in names if PLACE_BY_NAME[n].get("area") == area)
        a = AREAS[area]
        with st.expander(f"🗺️ {a['title']} — {here}"):
            if a["b1"]:
                ground, parking = st.tabs(["Ground floor (G)", "Parking B1"])
                ground.image(a["map"], caption=f"Ground floor: {a['title']} / {a['ar']}")
                parking.image(a["b1"], caption="Parking B1 under this area. Olive = public visitor parking.")
            else:
                st.image(a["map"], caption=f"Ground floor: {a['title']} / {a['ar']}")


with st.expander("🗺️ Msheireb maps: ground floor and parking B1"):
    st.markdown("**Ground floor (G)**")
    for tab, area in zip(st.tabs([a["title"] for a in AREAS.values()]), AREAS.values()):
        tab.image(area["map"])
    st.markdown("**Parking B1** — olive = public, purple = commercial, gold = VIP, teal = residential, grey = others")
    b1_areas = [a for a in AREAS.values() if a["b1"]]
    for tab, area in zip(st.tabs([a["title"] for a in b1_areas]), b1_areas):
        tab.image(area["b1"])

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        show(m["content"])
        if m.get("places"):
            show_places(m["places"])

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

    # Pull out the hidden TOPIC line (insights panel) and PLACES line (directions + maps)
    answer_lines, topic, places = [], None, []
    for line in text.splitlines():
        key = line.strip().strip("*").upper()
        if key.startswith("TOPIC:"):
            topic = line.split(":", 1)[1].strip().strip("*").strip()
        elif key.startswith("PLACES:"):
            for raw in line.split(":", 1)[1].split("|"):
                name = match_place(raw)
                if name and name not in places:
                    places.append(name)
        else:
            answer_lines.append(line)
    answer = "\n".join(answer_lines).strip()

    # The answer is drawn once, by the chat history loop above, after the rerun.
    st.session_state.messages.append({"role": "assistant", "content": answer, "places": places})
    if topic:
        st.session_state.questions.append(topic)
    st.rerun()
