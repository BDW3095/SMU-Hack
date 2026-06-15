# RoomGenie 🏠

AI-powered interior design tool that transforms a room photo into 4 styled redesigns and finds matching furniture on Shopee SG — all in one flow.

## What it does

1. **Upload** a photo of your room
2. **Describe** your room type and 3 must-haves (e.g. "large L-shaped sofa", "warm floor lamp")
3. **Generate** — Agnes AI produces 4 style variants (Minimalist, Scandinavian, Modern Industrial, Tropical/Rattan) while simultaneously searching Shopee for every furniture item
4. **Pick** your favourite design
5. **Email** yourself the chosen design + full Shopee shopping list

## Tech stack

| Layer | Tool |
|-------|------|
| UI | Streamlit |
| Image generation | Agnes Image 2.0 Flash |
| Furniture list | Agnes 2.0 Flash (chat) |
| Product search | Scrapeless → Shopee SG |
| Email | Gmail SMTP SSL |
| Image utils | Pillow |
| Click analytics | SQLite (built-in) |

## Setup

### 1. Install Python dependencies

```bash
C:\Users\<you>\AppData\Local\Programs\Python\Python313\python.exe -m pip install -r requirements.txt
```

### 2. Configure `.env`

Copy `.env.example` to `.env` and fill in your keys:

```
AGNES_API_KEY=sk-key1,sk-key2,sk-key3,...   # comma-separated; one used per image call
AGNES_BASE_URL=https://apihub.agnes-ai.com
SCRAPELESS_API_KEY=sk_...
GMAIL_SENDER_EMAIL=you@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx       # 16-char Google App Password (spaces OK)
IMGBB_API_KEY=...                            # optional — fallback if Agnes rejects base64
ADMIN_USERNAME=admin                         # admin dashboard login
ADMIN_PASSWORD=yourpassword                  # admin dashboard password
```

#### How to generate a Gmail App Password

1. Go to [myaccount.google.com](https://myaccount.google.com) and sign in with the account you put in `GMAIL_SENDER_EMAIL`
2. Navigate to **Security → How you sign in to Google → 2-Step Verification** and make sure it is **ON** (required before App Passwords appear)
3. Back on the Security page, search for **App Passwords** (or go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords))
4. Under "App name" type `RoomGenie` → click **Create**
5. Google shows a 16-character code like `abcd efgh ijkl mnop` — copy the whole thing (spaces included) into `GMAIL_APP_PASSWORD`
6. Click **Done**

> **SMU / Google Workspace accounts:** App Passwords work if your IT admin has enabled them. If you see an error, use a personal `@gmail.com` account as the sender instead.

### 3. (Optional) Custom loading screen

Drop a file into the `assets/` folder at the project root. The app checks for these in order and uses the first one it finds:

| File | Format |
|------|--------|
| `assets/loading.mp4` | Looping video (autoplays, muted) |
| `assets/loading.gif` | Animated GIF |
| `assets/loading.png` | Static image |
| `assets/loading.jpg` | Static image |

If no file is present, the app shows an animated emoji instead.

### 4. Run

```bash
C:\Users\<you>\AppData\Local\Programs\Python\Python313\Scripts\streamlit.exe run src\main.py
```

Then open [http://localhost:8501](http://localhost:8501) in your browser.

**Admin dashboard:** navigate to [http://localhost:8501/admin](http://localhost:8501/admin) and log in with the credentials from your `.env`. The dashboard shows Shopee click analytics (clicks per day, by category, top products) and lets you export a CSV report.

## Project structure

```
├── assets/              # Optional loading screen media (loading.mp4 / .gif / .png)
├── clicks.db            # SQLite click events (auto-created on first run)
├── src/
│   ├── main.py          # Streamlit app — 5-step navigation
│   ├── config.py        # Env-var config dataclass
│   ├── db.py            # SQLite helpers (init_db, log_click, get_stats)
│   ├── agents/
│   │   ├── image_agent.py      # Parallel Agnes image generation (4 styles)
│   │   └── furniture_agent.py  # Agnes chat → JSON furniture list
│   ├── clients/
│   │   ├── agnes_client.py     # Agnes HTTP client (key rotation, fallbacks)
│   │   └── scrapeless_client.py
│   ├── core/
│   │   └── interfaces.py       # ABCs (ImageGenerationProvider, EmailSender, …)
│   ├── pages/
│   │   └── admin.py            # Password-protected admin analytics dashboard
│   ├── services/
│   │   ├── shopee_service.py   # Scrapeless submit/poll, top-3 sort
│   │   └── email_service.py    # Gmail SMTP HTML email
│   ├── ui/
│   │   └── context_form.py     # Room type + must-haves form
│   └── utils/
│       └── image_utils.py      # JPEG normalisation, base64, imgbb upload
├── tests/
│   ├── test_image_agent.py
│   ├── test_furniture_agent.py
│   └── test_shopee_service.py
├── .env                 # Your secrets (never commit)
├── .env.example
├── requirements.txt
└── README.md
```

## Concurrency model

```
User submits context
        │
        ├── ThreadPoolExecutor(2)
        │       │
        │       ├── ImageAgent.generate_all_styles()   ← ThreadPoolExecutor(4)
        │       │       ├── Agnes key-1  → Minimalist image
        │       │       ├── Agnes key-2  → Scandinavian image
        │       │       ├── Agnes key-3  → Modern Industrial image
        │       │       └── Agnes key-4  → Tropical/Rattan image
        │       │
        │       └── FurnitureAgent.generate_list()
        │               └── ShopeeService.search_all()  ← ThreadPoolExecutor(6)
        │                       ├── Scrapeless → item 1
        │                       ├── Scrapeless → item 2
        │                       └── …
        │
        └── Display 2×2 grid + tabbed shopping list
```

## Admin dashboard

Navigate to `http://localhost:8501/admin` after starting the app. Log in with `ADMIN_USERNAME` / `ADMIN_PASSWORD` from your `.env`.

The dashboard tracks every "View on Shopee →" click and shows:

- **Total clicks** — headline KPI
- **Clicks per day** — bar chart (last 30 days)
- **Clicks by category** — which furniture types drive the most traffic
- **Top clicked products** — ranked product table with Shopee URLs
- **Recent clicks** — last 50 events with session IDs and timestamps
- **CSV export** — one-click download for Shopee reporting

Click data is stored in `clicks.db` (SQLite, auto-created on first run) at the project root. Each record captures: product ID, product name, category, Shopee URL, anonymous session ID, and UTC timestamp.

## API keys

| Service | Where to get |
|---------|-------------|
| Agnes AI | [apihub.agnes-ai.com](https://apihub.agnes-ai.com) |
| Scrapeless | [scrapeless.com](https://scrapeless.com) |
| imgbb (optional) | [api.imgbb.com](https://api.imgbb.com) |
| Gmail App Password | See setup instructions above |
