# TravelInDex 🗺️

> Frictionless travel inspiration saving — from social media to a beautiful web index in seconds.

---

## What It Is

1. You see a great restaurant on TikTok or Instagram
2. Tap **Share → TravelInDex Shortcut**
3. Pick a trip board
4. It's saved. Open the web app to browse later.

---

## Folder Structure

```
travelsave/
├── backend/
│   ├── main.py           FastAPI routes
│   ├── gemini.py         Gemini 1.5 Flash extraction
│   ├── db.py             Supabase client
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── index.html        TravelInDex web app
├── supabase/
│   └── schema.sql        Database schema
└── README.md
```

---

## Setup

### 1. Supabase

1. Create a project at [supabase.com](https://supabase.com)
2. Go to **SQL Editor** → paste `supabase/schema.sql` → Run
3. Copy your **Project URL** and **Service Role Key** from Settings → API

### 2. Gemini API

1. Go to [aistudio.google.com](https://aistudio.google.com)
2. Create an API key (free tier is generous)

### 3. Backend (local dev)

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with your keys

python main.py
# → http://localhost:8000
# → Docs at http://localhost:8000/docs
```

### 4. Deploy Backend → Render

1. Push your repo to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your repo, set **Root Directory** to `backend`
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Add environment variables from your `.env`
7. Deploy — Render gives you a free URL like `https://travelsave-xxxx.onrender.com`

### 5. Deploy Frontend → GitHub Pages

1. Edit `frontend/index.html` — change `API_BASE` to your Render URL:
   ```js
   const API_BASE = 'https://travelsave-xxxx.onrender.com';
   ```
2. Push to GitHub
3. Settings → Pages → Deploy from branch (`main`, `/frontend`)
4. Your site is live at `https://yourusername.github.io/travelsave/`

---

## iOS Shortcut Setup

Build a Shortcut with these actions:

1. **Receive input from Share Sheet** (type: Text / URLs)
2. **Get Device UUID** (use `Get Device Details` → "Device UUID")
3. **Get Contents of URL** → `GET {RENDER_URL}/trips/{Device UUID}`
4. **Get Value from JSON** → extract the array
5. **Choose from List** → show trip names
6. **Get Contents of URL** → `POST {RENDER_URL}/save`
   - Body: JSON `{"text": "...", "url": "...", "trip_id": "chosen trip", "device_id": "..."}`
7. **Show Result** → "Saved ✈️"

Then host the `.shortcut` file on iCloud and update the download link in `index.html`.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/save` | Extract + save places |
| GET | `/trips/{device_id}` | List trip names for device |
| GET | `/trip/{trip_id}?device_id=` | Get places in a trip |

### POST /save

```json
{
  "text": "Check out Café Central in Vienna! Best schnitzel 🏰",
  "url": "https://instagram.com/reel/...",
  "trip_id": "Europe Summer",
  "device_id": "ABC-123-XYZ"
}
```

Response:
```json
{
  "saved": 1,
  "places": [
    {"name": "Café Central", "city": "Vienna", "country": "Austria", "type": "cafe"}
  ]
}
```

---

## Future Upgrades (designed in from day 1)

- **Auth**: `device_id` → `user_id`, add Supabase Auth + Google OAuth
- **Payments**: Stripe for premium trip boards
- **Maps**: Add lat/lng and render places on a map view
- **Sharing**: Share trip boards with friends

---

## Cost

| Service | Cost |
|---------|------|
| Supabase | Free (500MB, 50k rows) |
| Render | Free (spins down after inactivity) |
| GitHub Pages | Free |
| Gemini 1.5 Flash | Free tier (generous) |
| **Total** | **$0/month** |
