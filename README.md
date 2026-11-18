# Msheireb Companion – prototype

An AI visitor guide for Msheireb Downtown Doha. Visitors chat in Qatari/Gulf Arabic, English or their own language and get 2–3 suggestions from Msheireb's real venue directory, adapted to the weather and time of day. A sidebar shows what visitors ask for, including needs Msheireb cannot meet yet.

## Files
- `app.py` – Streamlit app (chat + live context + insights panel)
- `data.json` – knowledge base: 162 Msheireb venues, shops, museums, activities, squares and transport
- `requirements.txt` – Python packages
- `maps/` – ground-floor and parking (B1) maps of the Msheireb areas, shown under answers
- `tools/enrich_from_osm.py` – adds English names, exact map pins and "near" notes to `data.json` from OpenStreetMap
- `sources/` – the OpenStreetMap places inside Msheireb Downtown's official outline, the outline itself, and `to_review.md` (places to check before adding)
- `secrets.toml.example` – template for the API key

## Run it
1. `pip install -r requirements.txt`
2. Get a free Gemini API key at https://aistudio.google.com/apikey
3. Copy `secrets.toml.example` to `.streamlit/secrets.toml` and paste the key
4. `streamlit run app.py`

## Visitor view and presenter view
- Visitors open the plain link. They see the chat, four one-tap starter buttons and an Arabic / English switch. The temperature comes from `DEFAULT_TEMP` in the secrets file and the time of day from the Doha clock.
- The presenter opens the same link with `?presenter=1` at the end (e.g. `http://localhost:8501/?presenter=1`). This adds the sidebar with the temperature and time controls and the insights panel.
- The insights panel counts topic labels from every visitor of the running app. No chat text is stored, and the counts reset when the app restarts.

## Updating the place data
`python tools/enrich_from_osm.py` re-applies the OpenStreetMap names and pins to `data.json`. Only places inside Msheireb Downtown's official outline are used. New places are never added automatically; they are listed in `sources/to_review.md` for a person to check. For the pilot, the same step can read Msheireb's official directory instead.

## Demo prompts
1. Arabic (any dialect, answered in Qatari dialect): `مرحبا انا ما بعرف وين روح وعندي بس ساعة اشرب فيها قهوة`
2. Heat: in the presenter view, set temperature to 44°C, then ask `I have one hour, what can I do?`
3. Unmet need: `Is there an ice skating rink for my kids?` – the presenter sidebar lists it under "Could not be met".
4. Lost in the parking: `I just came out of the elevator next to Virgin Active, how do I get to Harrods Tea Room?` – shows where you are and where to go, with both maps.

## Copyright
© 2026 Power Palm. All rights reserved. See [LICENSE](LICENSE). This code, its prompts and its data may not be copied, reused or redistributed without written permission from Power Palm.

Map images in `maps/` © Msheireb Properties, used for demonstration only.

Place names and pins in `sources/` and the `en`, `lat`, `lon` fields of `data.json`: © OpenStreetMap contributors, available under the Open Database License (https://www.openstreetmap.org/copyright).
