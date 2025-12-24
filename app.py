import re
import pandas as pd
import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs
from google_play_scraper import reviews, Sort
from google_play_scraper import app as gp_app


# ==========================================================
# SETTINGS
# ==========================================================

MAX_STOREFRONTS = None  # None = FULL all storefronts, or set 20 for faster testing


# ==========================================================
# LANGUAGE + COUNTRY HELPERS
# ==========================================================

LANGUAGE_NAMES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "nl": "Dutch",
    "ja": "Japanese",
    "ko": "Korean",
    "ru": "Russian",
    "ar": "Arabic",
    "tr": "Turkish",
    "zh": "Chinese",
    "hi": "Hindi",
    "sv": "Swedish",
    "da": "Danish",
    "no": "Norwegian",
    "fi": "Finnish",
    "bn": "Bangla",
    "uk": "Ukrainian",
    "vi": "Vietnamese",
    "id": "Indonesian",
    "ms": "Malay",
    "sw": "Swahili",
    "iw": "Hebrew",
    "cs": "Czech",
    "sk": "Slovak",
    "hu": "Hungarian",
    "ro": "Romanian",
    "bg": "Bulgarian",
    "si": "Sinhala",
    "ne": "Nepali",
}

COUNTRY_NAMES = {
    "us": "United States",
    "ca": "Canada",
    "mx": "Mexico",
    "gb": "United Kingdom",
    "ie": "Ireland",
    "fr": "France",
    "de": "Germany",
    "it": "Italy",
    "es": "Spain",
    "pt": "Portugal",
    "nl": "Netherlands",
    "be": "Belgium",
    "ch": "Switzerland",
    "at": "Austria",
    "se": "Sweden",
    "no": "Norway",
    "fi": "Finland",
    "dk": "Denmark",
    "pl": "Poland",
    "cz": "Czech Republic",
    "sk": "Slovakia",
    "hu": "Hungary",
    "ro": "Romania",
    "bg": "Bulgaria",
    "ua": "Ukraine",
    "ru": "Russia",
    "in": "India",
    "pk": "Pakistan",
    "bd": "Bangladesh",
    "np": "Nepal",
    "lk": "Sri Lanka",
    "id": "Indonesia",
    "ph": "Philippines",
    "vn": "Vietnam",
    "th": "Thailand",
    "my": "Malaysia",
    "sg": "Singapore",
    "jp": "Japan",
    "kr": "South Korea",
    "tw": "Taiwan",
    "hk": "Hong Kong",
    "tr": "Turkey",
    "sa": "Saudi Arabia",
    "ae": "United Arab Emirates",
    "eg": "Egypt",
    "il": "Israel",
    "za": "South Africa",
    "ng": "Nigeria",
    "ke": "Kenya",
    "br": "Brazil",
    "ar": "Argentina",
    "cl": "Chile",
    "co": "Colombia",
    "pe": "Peru",
    "au": "Australia",
    "nz": "New Zealand",
}


def lang_full_name(code: str) -> str:
    if not code:
        return ""
    code = code.split("-")[0].lower().strip()
    return LANGUAGE_NAMES.get(code, code)


def country_full_name(code: str) -> str:
    if not code:
        return ""
    code = code.lower().strip()
    return COUNTRY_NAMES.get(code, code.upper())


# ==========================================================
# APP INFO (ICON + TITLE)
# ==========================================================

@st.cache_data(show_spinner=False)
def get_google_app_info(package_name: str):
    try:
        data = gp_app(package_name, lang="en", country="us")
        return {"title": data.get("title", package_name), "icon": data.get("icon", "")}
    except Exception:
        return {"title": package_name, "icon": ""}


@st.cache_data(show_spinner=False)
def get_apple_app_info(app_id: str):
    try:
        url = f"https://itunes.apple.com/lookup?id={app_id}"
        resp = requests.get(url, timeout=15).json()
        results = resp.get("results", [])
        if results:
            r = results[0]
            return {"title": r.get("trackName", app_id), "icon": r.get("artworkUrl100", "")}
        return {"title": app_id, "icon": ""}
    except Exception:
        return {"title": app_id, "icon": ""}


# ==========================================================
# UI + COMMON HELPERS
# ==========================================================

def inject_css():
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.2rem; padding-bottom: 2.5rem; max-width: 1320px; }
        .rv-title { font-size: 40px; font-weight: 950; letter-spacing: -0.03em; margin-top: 20px; margin-bottom: 4px; }
        .rv-subtitle { font-size: 14px; color: rgba(0,0,0,0.62); margin-bottom: 14px; }

        .rv-card {
            background: #ffffff;
            border: 1px solid rgba(0,0,0,0.08);
            border-radius: 18px;
            padding: 18px 18px;
            box-shadow: 0 12px 32px rgba(0,0,0,0.06);
            margin-bottom: 16px;
        }
        .rv-card-title { font-size: 16px; font-weight: 900; margin-bottom: 10px; }
        .rv-muted { font-size: 13px; color: rgba(0,0,0,0.55); }

        .stButton > button {
            border-radius: 14px !important;
            font-weight: 900 !important;
            padding: 0.85rem 1.2rem !important;
            width: 100%;
        }
        div[data-baseweb="input"] input { border-radius: 12px !important; }
        div[data-baseweb="select"] > div { border-radius: 12px !important; }
        [data-testid="stMetricLabel"] p { font-weight: 850; }

        /* PREMIUM TABS */
        div[data-testid="stTabs"] { margin-top: 8px; }
        button[data-baseweb="tab"] {
            font-weight: 900;
            font-size: 14px;
            border-radius: 999px !important;
            padding: 10px 18px !important;
            margin-right: 8px !important;
            background: rgba(0,0,0,0.04) !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            background: rgba(255, 0, 0, 0.12) !important;
            border: 1px solid rgba(255, 0, 0, 0.25) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def style_by_star_background(styler):
    def row_style(row):
        star = row.get("Star", None)
        if star in [1, 2]:
            return ["background-color: rgba(255, 0, 0, 0.10); color: #B00020;"] * len(row)
        if star in [3, 4]:
            return ["background-color: rgba(255, 193, 7, 0.16); color: #6B4E00;"] * len(row)
        return [""] * len(row)

    return styler.apply(row_style, axis=1)


def star_counts(df: pd.DataFrame):
    counts = {s: 0 for s in [1, 2, 3, 4, 5]}
    if df.empty or "Star" not in df.columns:
        return counts
    vc = df["Star"].value_counts(dropna=False).to_dict()
    for s in counts.keys():
        counts[s] = int(vc.get(s, 0))
    return counts


def show_star_metrics(df: pd.DataFrame):
    counts = star_counts(df)
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("⭐ 1 Star", counts[1])
    m2.metric("⭐ 2 Star", counts[2])
    m3.metric("⭐ 3 Star", counts[3])
    m4.metric("⭐ 4 Star", counts[4])
    m5.metric("⭐ 5 Star", counts[5])


def apply_filters(df: pd.DataFrame, star_filter, search_text: str):
    filtered = df.copy()
    if filtered.empty:
        return filtered

    if "Star" in filtered.columns and star_filter:
        filtered = filtered[filtered["Star"].isin(star_filter)]

    q = (search_text or "").strip().lower()
    if q:
        note = filtered.get("Review Note", pd.Series([""] * len(filtered))).fillna("").astype(str).str.lower()
        filtered = filtered[note.str.contains(re.escape(q), regex=True)]

    return filtered


def parse_date_range(date_range):
    def flatten_once(x):
        if isinstance(x, (list, tuple)) and len(x) == 1 and isinstance(x[0], (list, tuple)):
            return x[0]
        return x

    prev = None
    while prev != date_range:
        prev = date_range
        date_range = flatten_once(date_range)

    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = date_range
        end_date = date_range

    while isinstance(start_date, (list, tuple)):
        start_date = start_date[0]
    while isinstance(end_date, (list, tuple)):
        end_date = end_date[-1]

    start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    end_dt = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)

    start_label = start_date.strftime("%d %B, %Y")
    end_label = end_date.strftime("%d %B, %Y")
    days_selected = (end_date - start_date).days + 1
    range_label = f"{start_label} - {end_label}"

    return start_dt, end_dt, range_label, days_selected


def format_datetime(dt: datetime) -> str:
    if not dt:
        return ""
    dt_local = dt.astimezone(timezone.utc)
    date_part = dt_local.strftime("%d %B, %Y")
    time_part = dt_local.strftime("%I:%M %p").lstrip("0")
    return f"{date_part} - {time_part}"


def standardize_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    for col in ["User Name", "Review Note", "Star", "App Version", "Device Language", "Country", "dt_utc"]:
        if col not in df.columns:
            df[col] = ""

    df["Date & Time"] = df["dt_utc"].apply(format_datetime)
    df = df.sort_values("dt_utc", ascending=False).reset_index(drop=True)

    final_cols = [
        "Date & Time",
        "User Name",
        "Review Note",
        "Star",
        "App Version",
        "Device Language",
        "Country",
    ]
    return df[final_cols]


# ==========================================================
# GLOBAL CATEGORY + APP LISTS
# ==========================================================

CATEGORIES = ["Kids Games", "Parents Games", "Applications"]

GOOGLE_APPS = {
    "Kids Games": {
            "ABC Kids: Tracing & Phonics": "com.rvappstudios.abc_kids_toddler_tracing_phonics",
            "Spelling & Phonics: Kids Games": "com.rvappstudios.abc.spelling.toddler.spell.phonics",
            "123 Numbers - Count & Tracing": "com.rvappstudios.numbers123.toddler.counting.tracing",
            "Puzzle Kids: Jigsaw Puzzles": "com.rvappstudios.jigsaw.puzzles.kids",
            "Math Kids: Math Games For Kids": "com.rvappstudios.math.kids.counting",
            "Color Kids: Coloring Games": "com.rvappstudios.shapes.colors.toddler",
            "Kids Multiplication Math Games": "com.rvappstudios.kids.multiplication.games.multiply.math",
            "Baby Games: Piano & Baby Phone": "com.rvappstudios.baby.games.piano.phone.kids",
            "Coloring Games: Color & Paint": "com.rvappstudios.kids.coloring.book.color.painting",
            "Learn to Read: Kids Games": "com.rvappstudios.sight.words.phonics.reading.kids.games",
            "Math Games: Math for Kids": "com.rvappstudios.math.games.kids.addition.subtraction.multiplication.division",
            "Kids Math: Math Games for Kids": "com.rvappstudios.montessori.math.games.kids.number.counting",
            "Drawing Games: Draw & Color": "com.rvappstudios.kids.drawing.games.coloring.book.paint",
            "Kids Games: For Toddlers 3-5": "com.rvappstudios.baby.toddler.kids.games.learning.activity",
            "Kids Toddler & Preschool Games": "com.rvappstudios.toddler.preschool.kids.learning.games",
            "Baby Phone & Kids Games": "com.rvappstudios.baby.phone.kids.games.toddler.learning.apps.lucas.and.friends",
            "Kids Music: Piano, Xylo, Drums": "com.rvappstudios.kids.games.music.baby.piano.songs.lucas.and.friends",
    },
    "Parents Games": {
    "Jigsaw Puzzles: Picture Puzzle": "com.rvappstudios.jigsaw.puzzles",
    "Veggies Cut: Logic Puzzle Game": "com.rvappstudios.veggies.cut.logic.puzzle.adult.game",
    "Tangram Puzzle: Polygrams Game": "com.rvappstudios.tangram.blocks.puzzle.brain.games",
},
    "Applications": {
"App Locker: Privacy Apps Lock": "=com.rvappstudios.applock.protect.lock.app",
"Duplicate File Remover": "com.rvappstudios.duplicate.similar.files.photo.finder.cleaner",
"Phone Storage Cleaner: Cleanup": "com.rvappstudios.phone.storage.cleaner.disk.space.cleanup.duplicate.remover",
"Smart Calc: Daily Calculator": "com.rvappstudios.calculator.free.app",
"Magnifying Glass + Flashlight": "com.rvappstudios.magnifyingglass",
"Flash Alert: Call & SMS": "com.rvappstudios.Flash.Alerts.LED.Call.SMS.Flashlight",
"Alarm Clock: Mornings & Naps": "com.rvappstudios.alarm.clock.smart.sleep.timer.music",

    }
}

APPLE_APPS = {
    "Kids Games": {
        "ABC Kids: Tracing & Phonics": "1112482869",
        "Spelling & Phonics: Kids Games": "1186728253",
        "123 Numbers - Count & Tracing": "1210356444",
        "Puzzle Kids: Jigsaw Puzzles": "1244400052",
        "Math Kids: Math Games For Kids": "1272098657",
        "Color Kids: Coloring Games": "1272085786",
        "Kids Multiplication Math Games": "1455322707",
        "Baby Games: Piano & Baby Phone": "1455967837",
        "Coloring Games: Color & Paint": "1480696573",
        "Learn to Read: Kids Games": "1498466300",
        "Math Games: Math for Kids": "1525694602",
        "Kids Math: Math Games for Kids": "1565484251",
        "Drawing Games: Draw & Color": "1547228861",
        "Kids Games: For Toddlers 3-5": "1613310657",
        "Kids Toddler & Preschool Games": "6472886437",
        "Baby Phone & Kids Games": "id6744884306",
        "Kids Music: Piano, Xylo, Drums": "6747074172",
    },
    "Parents Games": {
        "Jigsaw Puzzles: Photo Puzzles": "1440151043",
        "Find The Differences: Spot It": "1475757108",
    },
    "Applications": {
        "Best Flash Light - Flashlight": "429177928",
        "Magnifying Glass + Flashlight": "908717824",
        "Alarm Clock ◎": "450993079",
    }
}

MICROSOFT_APPS = {
    "Kids Games": {
        "Coloring Games (Microsoft Store)": "9phq2rx60xgr",
    },
    "Parents Games": {},
    "Applications": {}
}

AMAZON_APPS = {
    "Kids Games": {
        "Coloring Games (Amazon)": "B08156J9VN",
    },
    "Parents Games": {},
    "Applications": {}
}


# ==========================================================
# FULL STOREFRONTS LIST (60+)
# ==========================================================

GOOGLE_ALL_STOREFRONTS = [
    ("us", "en", "United States"),
    ("ca", "en", "Canada"),
    ("mx", "es", "Mexico"),
    ("gb", "en", "United Kingdom"),
    ("ie", "en", "Ireland"),
    ("fr", "fr", "France"),
    ("de", "de", "Germany"),
    ("it", "it", "Italy"),
    ("es", "es", "Spain"),
    ("pt", "pt", "Portugal"),
    ("nl", "nl", "Netherlands"),
    ("be", "fr", "Belgium"),
    ("ch", "de", "Switzerland"),
    ("at", "de", "Austria"),
    ("se", "sv", "Sweden"),
    ("no", "no", "Norway"),
    ("fi", "fi", "Finland"),
    ("dk", "da", "Denmark"),
    ("pl", "pl", "Poland"),
    ("cz", "cs", "Czech Republic"),
    ("sk", "sk", "Slovakia"),
    ("hu", "hu", "Hungary"),
    ("ro", "ro", "Romania"),
    ("bg", "bg", "Bulgaria"),
    ("ua", "uk", "Ukraine"),
    ("ru", "ru", "Russia"),
    ("in", "en", "India"),
    ("pk", "en", "Pakistan"),
    ("bd", "bn", "Bangladesh"),
    ("np", "ne", "Nepal"),
    ("lk", "si", "Sri Lanka"),
    ("id", "id", "Indonesia"),
    ("ph", "en", "Philippines"),
    ("vn", "vi", "Vietnam"),
    ("th", "th", "Thailand"),
    ("my", "ms", "Malaysia"),
    ("sg", "en", "Singapore"),
    ("jp", "ja", "Japan"),
    ("kr", "ko", "South Korea"),
    ("tw", "zh", "Taiwan"),
    ("hk", "zh", "Hong Kong"),
    ("tr", "tr", "Turkey"),
    ("sa", "ar", "Saudi Arabia"),
    ("ae", "ar", "United Arab Emirates"),
    ("eg", "ar", "Egypt"),
    ("il", "iw", "Israel"),
    ("za", "en", "South Africa"),
    ("ng", "en", "Nigeria"),
    ("ke", "sw", "Kenya"),
    ("br", "pt", "Brazil"),
    ("ar", "es", "Argentina"),
    ("cl", "es", "Chile"),
    ("co", "es", "Colombia"),
    ("pe", "es", "Peru"),
    ("au", "en", "Australia"),
    ("nz", "en", "New Zealand"),
]

APPLE_COUNTRIES = [c for c, _, _ in GOOGLE_ALL_STOREFRONTS]


# ==========================================================
# GOOGLE PLAY FUNCTIONS
# ==========================================================

def package_from_play_url(play_url: str) -> str:
    qs = parse_qs(urlparse(play_url).query)
    if "id" in qs and qs["id"]:
        return qs["id"][0]
    m = re.search(r"[?&]id=([^&]+)", play_url)
    if m:
        return m.group(1)
    raise ValueError("Could not find package id in URL. Must include ?id=com.example.app")


def fetch_google_reviews_date_range(package_name: str, start_dt: datetime, end_dt: datetime, lang: str, country: str, max_pages: int = 50):
    rows = []
    token = None
    pages = 0

    while pages < max_pages:
        result, token = reviews(
            package_name,
            lang=lang,
            country=country,
            sort=Sort.NEWEST,
            count=200,
            continuation_token=token,
        )
        pages += 1

        if not result:
            break

        stop = False
        for r in result:
            at = r.get("at")
            if not at:
                continue

            at = at.replace(tzinfo=timezone.utc) if at.tzinfo is None else at.astimezone(timezone.utc)

            if at < start_dt:
                stop = True
                continue
            if at > end_dt:
                continue

            rows.append(
                {
                    "dt_utc": at,
                    "User Name": r.get("userName") or "",
                    "Review Note": r.get("content") or "",
                    "Star": r.get("score"),
                    "App Version": r.get("reviewCreatedVersion") or "",
                    "Device Language": lang_full_name(lang),
                    "Country": country_full_name(country),
                }
            )

        if stop or token is None:
            break

    return pd.DataFrame(rows)


def fetch_google_all_countries(package_name: str, start_dt: datetime, end_dt: datetime):
    frames = []
    storefronts = GOOGLE_ALL_STOREFRONTS[:MAX_STOREFRONTS] if MAX_STOREFRONTS else GOOGLE_ALL_STOREFRONTS
    total = len(storefronts)

    status_box = st.status("Collecting Google Play reviews...", expanded=False)
    progress = st.progress(0)

    for i, (country_code, lang_code, country_name) in enumerate(storefronts, start=1):
        status_box.update(label=f"Google: {country_name} • {i}/{total}")
        progress.progress(int((i / total) * 100))

        try:
            df = fetch_google_reviews_date_range(package_name, start_dt, end_dt, lang_code, country_code)
            if not df.empty:
                frames.append(df)
        except Exception:
            continue

    progress.progress(100)
    status_box.update(label="Merging Google results…", state="running")

    if not frames:
        status_box.update(label="Done (no reviews).", state="complete")
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.drop_duplicates(subset=["User Name", "dt_utc", "Review Note"], keep="first")
    status_box.update(label=f"Done. Merged {len(combined)} unique Google reviews.", state="complete")
    return combined


# ==========================================================
# APPLE FUNCTIONS
# ==========================================================

def apple_app_id_from_url(url: str) -> str:
    m = re.search(r"/id(\d+)", url)
    if not m:
        raise ValueError("Could not find Apple App ID. URL must include /id123456789")
    return m.group(1)


def fetch_apple_reviews_country(app_id: str, country: str, start_dt: datetime, end_dt: datetime, max_pages: int = 10):
    rows = []
    for page in range(1, max_pages + 1):
        url = f"https://itunes.apple.com/{country}/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json"

        try:
            resp = requests.get(url, timeout=20)
            if resp.status_code != 200:
                break
            data = resp.json()
        except Exception:
            break

        entries = data.get("feed", {}).get("entry", [])
        if not entries or len(entries) <= 1:
            break

        for e in entries:
            if "author" not in e or "im:rating" not in e:
                continue

            updated = e.get("updated", {}).get("label", "")
            try:
                at = pd.to_datetime(updated, utc=True).to_pydatetime()
            except Exception:
                continue

            at = at.replace(tzinfo=timezone.utc) if at.tzinfo is None else at.astimezone(timezone.utc)

            if at < start_dt:
                return pd.DataFrame(rows)
            if at > end_dt:
                continue

            title = e.get("title", {}).get("label", "") or ""
            note = e.get("content", {}).get("label", "") or ""
            merged_note = f"{title}\n\n{note}".strip() if title else note

            rows.append(
                {
                    "dt_utc": at,
                    "User Name": e.get("author", {}).get("name", {}).get("label", "") or "",
                    "Review Note": merged_note,
                    "Star": int(e.get("im:rating", {}).get("label", 0)),
                    "App Version": e.get("im:version", {}).get("label", "") or "",
                    "Device Language": "",
                    "Country": country_full_name(country),
                }
            )

    return pd.DataFrame(rows)


def fetch_apple_all_countries(app_id: str, start_dt: datetime, end_dt: datetime):
    frames = []
    storefronts = APPLE_COUNTRIES[:MAX_STOREFRONTS] if MAX_STOREFRONTS else APPLE_COUNTRIES
    total = len(storefronts)

    status_box = st.status("Collecting Apple reviews...", expanded=False)
    progress = st.progress(0)

    for i, c in enumerate(storefronts, start=1):
        status_box.update(label=f"Apple: {country_full_name(c)} • {i}/{total}")
        progress.progress(int((i / total) * 100))

        try:
            df = fetch_apple_reviews_country(app_id, c, start_dt, end_dt)
            if not df.empty:
                frames.append(df)
        except Exception:
            continue

    progress.progress(100)
    status_box.update(label="Merging Apple results…", state="running")

    if not frames:
        status_box.update(label="Done (no reviews).", state="complete")
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.drop_duplicates(subset=["User Name", "dt_utc", "Review Note"], keep="first")
    status_box.update(label=f"Done. Merged {len(combined)} unique Apple reviews.", state="complete")
    return combined


# ==========================================================
# MICROSOFT + AMAZON (best effort)
# ==========================================================

def microsoft_product_id_from_url(url: str) -> str:
    m = re.search(r"/detail/([A-Za-z0-9]{6,})", url)
    if not m:
        raise ValueError("Could not find Microsoft Product ID. Must include /detail/<id>")
    return m.group(1)


def fetch_microsoft_reviews(product_id: str):
    rows = []
    headers = {"User-Agent": "Mozilla/5.0"}

    url = f"https://apps.microsoft.com/detail/{product_id}?hl=en-us&gl=us"

    try:
        r = requests.get(url, headers=headers, timeout=25)
        if r.status_code != 200:
            return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

    soup = BeautifulSoup(r.text, "lxml")
    review_blocks = soup.find_all("div", class_=re.compile("review", re.I))

    for rb in review_blocks:
        txt = rb.get_text(" ", strip=True)
        mstar = re.search(r"(\d)\s*out of 5", txt)
        if not mstar:
            continue
        star = int(mstar.group(1))

        rows.append(
            {
                "dt_utc": None,
                "User Name": "",
                "Review Note": txt,
                "Star": star,
                "App Version": "",
                "Device Language": "",
                "Country": "United States",
            }
        )

    return pd.DataFrame(rows)


def amazon_asin_from_url(url: str) -> str:
    m = re.search(r"/dp/([A-Z0-9]{10})", url)
    if not m:
        raise ValueError("Could not find Amazon ASIN. Must include /dp/BXXXXXXXXX")
    return m.group(1)


def fetch_amazon_reviews(asin: str, max_pages: int = 3):
    rows = []
    headers = {"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"}

    for page in range(1, max_pages + 1):
        url = f"https://www.amazon.com/product-reviews/{asin}/?pageNumber={page}"

        try:
            r = requests.get(url, headers=headers, timeout=25)
            if r.status_code != 200:
                break
        except Exception:
            break

        if "captcha" in r.text.lower() or "robot check" in r.text.lower():
            return pd.DataFrame([{
                "dt_utc": None,
                "User Name": "",
                "Review Note": "Amazon blocked the request (captcha/bot check). Use Amazon Product Advertising API for stable results.",
                "Star": "",
                "App Version": "",
                "Device Language": "",
                "Country": "United States",
            }])

        soup = BeautifulSoup(r.text, "lxml")
        blocks = soup.select("div[data-hook='review']")
        if not blocks:
            break

        for b in blocks:
            star_txt = b.select_one("i[data-hook='review-star-rating'] span")
            star = ""
            if star_txt:
                mstar = re.search(r"(\d+(\.\d+)?)", star_txt.get_text(strip=True))
                if mstar:
                    star = int(float(mstar.group(1)))

            body = b.select_one("span[data-hook='review-body']")
            text = body.get_text(" ", strip=True) if body else ""

            rows.append(
                {
                    "dt_utc": None,
                    "User Name": "",
                    "Review Note": text,
                    "Star": star,
                    "App Version": "",
                    "Device Language": "",
                    "Country": "United States",
                }
            )

    return pd.DataFrame(rows)


# ==========================================================
# APP MAIN UI
# ==========================================================

st.set_page_config(page_title="RV AppStudios - Store Reviews Tool", layout="wide")
inject_css()

st.markdown('<div class="rv-title">RV AppStudios - Store Reviews Tool</div>', unsafe_allow_html=True)
st.markdown('<div class="rv-subtitle">Choose Category and Date Range globally. Then fetch and filter reviews per store.</div>', unsafe_allow_html=True)

# Premium Global Filters
st.markdown(
    """
    <div class="rv-card" style="padding: 16px 18px; margin-bottom: 12px;">
      <div style="display:flex; align-items:center; justify-content:space-between; gap:12px;">
        <div>
          <div style="font-size:15px; font-weight:950; margin-bottom:2px;">Global Filters</div>
          <div class="rv-muted">Applies across all stores (Google, Apple, Microsoft, Amazon)</div>
        </div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

row1, row2 = st.columns([1.25, 1.75], gap="large")

with row1:
    global_category = st.radio("Category", CATEGORIES, horizontal=True, key="global_category")

with row2:
    global_date_range = st.date_input(
        "Date Range (From → To)",
        value=(pd.Timestamp.utcnow().date() - pd.Timedelta(days=7), pd.Timestamp.utcnow().date()),
        key="global_date_range"
    )

global_start_dt, global_end_dt, global_range_label, global_days_selected = parse_date_range(global_date_range)

st.markdown(
    f"""
    <div class="rv-card" style="padding: 12px 16px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <div style="font-size:14px; font-weight:950; margin-bottom:2px;">Selected</div>
                <div class="rv-muted">{global_range_label}</div>
            </div>
            <div style="
                background: rgba(0,0,0,0.06);
                border: 1px solid rgba(0,0,0,0.10);
                padding: 10px 14px;
                border-radius: 14px;
                font-weight: 950;
                font-size: 13px;">
                {global_days_selected} days
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Premium Tabs
tab_google, tab_apple, tab_microsoft, tab_amazon = st.tabs([
    "🟢 Google Play",
    "🍎 Apple App Store",
    "🪟 Microsoft Store",
    "🛒 Amazon"
])


# ==========================================================
# PREMIUM DASHBOARD TAB TEMPLATE
# ==========================================================

def dashboard_tab(store_label, store_apps_by_category, link_label, link_placeholder, extract_id_fn,
                  fetch_fn, info_fn, session_key, note=""):

    st.markdown(f"## {store_label}")
    if note:
        st.caption(note)
    st.write("")

    c1, c2, c3 = st.columns([1.55, 1.05, 1.10], gap="large")

    with c1:
        st.markdown("### App Selection")
        mode = st.radio(
            "Select input type",
            ["Dropdown (recommended)", f"Paste {link_label}"],
            horizontal=True,
            key=f"{session_key}_mode"
        )

        if mode == "Dropdown (recommended)":
            category_apps = store_apps_by_category.get(global_category, {})
            if not category_apps:
                st.warning(f"No apps listed under {global_category}. Add apps in code.")
                return

            app_label = st.selectbox("Select app", list(category_apps.keys()), key=f"{session_key}_app")
            app_id = category_apps[app_label]
            st.text_input("App Identifier", value=app_id, disabled=True)

        else:
            url = st.text_input(f"Paste {link_label}", value=link_placeholder, key=f"{session_key}_url")
            try:
                app_id = extract_id_fn(url)
                st.success(f"Detected ID: {app_id}")
            except Exception as e:
                st.error(str(e))
                return

    with c2:
        st.markdown("### Filters")
        star_filter = st.multiselect(
            "Stars",
            [1, 2, 3, 4, 5],
            default=[1, 2, 3, 4, 5],
            key=f"{session_key}_star_filter"
        )

        search_text = st.text_input(
            "Search keyword",
            value="",
            placeholder="crash, ads, language...",
            key=f"{session_key}_search"
        )

    with c3:
        st.markdown("### Fetch")
        st.markdown(f"**{global_range_label}**")
        st.caption(f"Days selected: {global_days_selected}")

        fetch_clicked = st.button(
            "Fetch Reviews",
            type="primary",
            use_container_width=True,
            key=f"{session_key}_fetch"
        )

    st.divider()

    if session_key not in st.session_state:
        st.session_state[session_key] = pd.DataFrame()

    if fetch_clicked:
        try:
            with st.spinner(f"Fetching {store_label} reviews..."):
                st.session_state[session_key] = fetch_fn(app_id, global_start_dt, global_end_dt)
        except Exception as e:
            st.error(str(e))

    raw_df = st.session_state[session_key].copy()

    if not raw_df.empty and info_fn:
        info = info_fn(app_id)
        colx, coly = st.columns([0.12, 0.88], gap="large")
        with colx:
            if info.get("icon"):
                st.image(info["icon"], width=80)
        with coly:
            st.markdown(f"### {info.get('title', '')}")
            st.caption(f"{store_label} • {global_range_label} • Category: {global_category}")
        st.write("")

    df = standardize_table(raw_df) if not raw_df.empty else pd.DataFrame()
    filtered = apply_filters(df, star_filter, search_text)

    st.markdown("### Star counts")
    show_star_metrics(df)
    st.write("")

    st.markdown("### Reviews")
    if df.empty:
        st.info("Click Fetch Reviews to load reviews.")
    else:
        st.caption(f"Showing {len(filtered)} of {len(df)} reviews after filters.")
        st.dataframe(style_by_star_background(filtered.style), use_container_width=True, height=650)

        st.download_button(
            "Download CSV (Filtered)",
            data=filtered.to_csv(index=False).encode("utf-8"),
            file_name=f"{store_label.lower().replace(' ', '_')}_reviews.csv",
            mime="text/csv",
            use_container_width=True,
        )


# Run tabs
with tab_google:
    dashboard_tab(
        store_label="Google Play Reviews",
        store_apps_by_category=GOOGLE_APPS,
        link_label="Play Store link",
        link_placeholder="https://play.google.com/store/apps/details?id=com.example.app",
        extract_id_fn=package_from_play_url,
        fetch_fn=fetch_google_all_countries,
        info_fn=get_google_app_info,
        session_key="google_raw",
    )

with tab_apple:
    dashboard_tab(
        store_label="Apple App Store Reviews",
        store_apps_by_category=APPLE_APPS,
        link_label="App Store link",
        link_placeholder="https://apps.apple.com/app/anything/id123456789",
        extract_id_fn=apple_app_id_from_url,
        fetch_fn=fetch_apple_all_countries,
        info_fn=get_apple_app_info,
        session_key="apple_raw",
    )

with tab_microsoft:
    dashboard_tab(
        store_label="Microsoft Store Reviews (Best Effort)",
        store_apps_by_category=MICROSOFT_APPS,
        link_label="Microsoft Store link",
        link_placeholder="https://apps.microsoft.com/detail/XXXXXXXXXXXX",
        extract_id_fn=microsoft_product_id_from_url,
        fetch_fn=lambda pid, s, e: fetch_microsoft_reviews(pid),
        info_fn=None,
        session_key="ms_raw",
        note="Microsoft does not provide a stable public reviews API. This is best-effort scraping."
    )

with tab_amazon:
    dashboard_tab(
        store_label="Amazon Reviews (Best Effort)",
        store_apps_by_category=AMAZON_APPS,
        link_label="Amazon link",
        link_placeholder="https://www.amazon.com/dp/BXXXXXXXXX",
        extract_id_fn=amazon_asin_from_url,
        fetch_fn=lambda asin, s, e: fetch_amazon_reviews(asin),
        info_fn=None,
        session_key="am_raw",
        note="Amazon often blocks scraping (captcha). For stable results, use Amazon Product Advertising API."
    )
