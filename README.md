# Msheireb Companion – prototype

An AI visitor guide for Msheireb Downtown Doha. Visitors chat in Qatari/Gulf Arabic, English or their own language and get 2–3 suggestions from Msheireb's real venue directory, adapted to the weather and time of day. A sidebar shows what visitors ask for, including needs Msheireb cannot meet yet.

## Files
- `app.py` – Streamlit app (chat + live context + insights panel)
- `data.json` – knowledge base: 162 Msheireb venues, shops, museums, activities, squares and transport
- `requirements.txt` – Python packages
- `maps/` – ground-floor and parking (B1) maps of the Msheireb areas, shown under answers
- `secrets.toml.example` – template for the API key

## Run it
1. `pip install -r requirements.txt`
2. Get a free Gemini API key at https://aistudio.google.com/apikey
3. Copy `secrets.toml.example` to `.streamlit/secrets.toml` and paste the key
4. `streamlit run app.py`

## Demo prompts
1. Arabic (any dialect, answered in Qatari dialect): `مرحبا انا ما بعرف وين روح وعندي بس ساعة اشرب فيها قهوة`
2. Heat: set temperature to 44°C, then ask `I have one hour, what can I do?`
3. Unmet need: `Is there an ice skating rink for my kids?` – the sidebar logs it as "unmet: ice skating".
4. Lost in the parking: `I just came out of the elevator next to Virgin Active, how do I get to Harrods Tea Room?` – shows where you are and where to go, with both maps.
