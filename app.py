import re
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, parse_qs
from google_play_scraper import reviews, Sort


# ----------------------------
# App list (Dropdown)
# ----------------------------
APPS = {
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
}


# ----------------------------
# ALL Countries FULL list (≈60 storefronts)
# (country_code, lang_code, country_name)
# ----------------------------
ALL_STOREFRONTS = [
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


def to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def fetch_last_days(package_name: str, days: int, lang: str, country: str, max_pages: int = 50) -> pd.DataFrame:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
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
            at = to_utc(r.get("at"))
            if at < cutoff:
                stop = True
                continue

            rows.append(
                {
                    "reviewId": r.get("reviewId"),
                    "userName": r.get("userName"),
                    "score": r.get("score"),
                    "thumbsUpCount": r.get("thumbsUpCount"),
                    "reviewCreatedVersion": r.get("reviewCreatedVersion"),
                    "at_utc": at.isoformat(),
                    "content": r.get("content") or "",
                    "replyContent": r.get("replyContent") or "",
                    "repliedAt_utc": (to_utc(r["repliedAt"]).isoformat() if r.get("repliedAt") else ""),
                }
            )

        if stop or token is None:
            break

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("at_utc", ascending=False)
    return df


def fetch_all_storefronts_full(package_name: str, days: int) -> pd.DataFrame:
    frames = []

    # compact, nicer progress UI
    status_box = st.status("Collecting reviews across storefronts…", expanded=False)
    progress = st.progress(0)

    total = len(ALL_STOREFRONTS)
    for i, (country_code, lang_code, country_name) in enumerate(ALL_STOREFRONTS, start=1):
        status_box.update(label=f"Collecting: {country_name} ({country_code}) • {i}/{total}")
        progress.progress(int((i / total) * 100))

        try:
            df = fetch_last_days(
                package_name=package_name,
                days=days,
                lang=lang_code,
                country=country_code,
            )
            if not df.empty:
                df["country_name"] = country_name
                df["country_code"] = country_code
                df["storefront_language"] = lang_code
                frames.append(df)
        except Exception:
            continue

    status_box.update(label="Merging results…", state="running")
    progress.progress(100)

    if not frames:
        status_box.update(label="Done (no reviews returned).", state="complete")
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values("at_utc", ascending=False)
    combined = combined.drop_duplicates(subset=["reviewId"], keep="first")

    status_box.update(label=f"Done. Merged {len(combined)} unique reviews.", state="complete")
    return combined


def format_for_ui(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    at_dt = pd.to_datetime(df["at_utc"], errors="coerce", utc=True)
    df["Date"] = at_dt.dt.strftime("%d %B %Y")

    df = df.rename(
        columns={
            "score": "Star",
            "reviewCreatedVersion": "App Version",
            "content": "Review Note",
            "replyContent": "Reply Message",
            "userName": "User Name",
            "thumbsUpCount": "Thumbs Up",
            "country_name": "Country",
            "reviewId": "Review ID",
        }
    )

    # hide these columns completely
    hide_cols = {"repliedAt_utc", "country_code", "storefront_language", "at_utc"}
    df = df[[c for c in df.columns if c not in hide_cols]]

    # put Review ID at the end
    if "Review ID" in df.columns:
        cols = [c for c in df.columns if c != "Review ID"] + ["Review ID"]
        df = df[cols]

    return df


def star_counts(df: pd.DataFrame):
    counts = {s: 0 for s in [1, 2, 3, 4, 5]}
    if df.empty or "Star" not in df.columns:
        return counts
    vc = df["Star"].value_counts(dropna=False).to_dict()
    for s in counts.keys():
        counts[s] = int(vc.get(s, 0))
    return counts


def style_by_star_background(styler):
    # background highlight (more visible than font-only)
    def row_style(row):
        star = row.get("Star", None)
        if star in [1, 2]:
            return ["background-color: rgba(255, 0, 0, 0.10); color: #B00020;"] * len(row)
        if star in [3, 4]:
            return ["background-color: rgba(255, 193, 7, 0.14); color: #7A5B00;"] * len(row)
        if star == 5:
            return ["background-color: rgba(0, 128, 0, 0.10); color: #0B6B0B;"] * len(row)
        return [""] * len(row)

    return styler.apply(row_style, axis=1)


def inject_css():
    st.markdown(
        """
        <style>
          /* tighten top padding */
          .block-container { padding-top: 1.2rem; padding-bottom: 2.5rem; max-width: 1200px; }

          /* nicer buttons */
          .stButton > button {
            border-radius: 12px !important;
            padding: 0.55rem 0.95rem !important;
            font-weight: 600 !important;
          }

          /* “cards” */
          .rv-card {
            background: rgba(255,255,255,0.7);
            border: 1px solid rgba(0,0,0,0.07);
            border-radius: 16px;
            padding: 14px 16px;
            box-shadow: 0 6px 20px rgba(0,0,0,0.04);
          }

          /* headline */
          .rv-title {
        font-size: 30px;
  font-weight: 800;
  letter-spacing: -0.02em;
  margin-top: 32px;
  margin-bottom: 6px;
  line-height: 1.2;
          }
          .rv-subtitle {
            font-size: 14px;
            color: rgba(0,0,0,0.6);
            margin-top: 0px;
          }

          /* metric labels a bit nicer */
          [data-testid="stMetricLabel"] p { font-weight: 600; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ----------------------------
# UI
# ----------------------------
st.set_page_config(page_title="Google Play Reviews Tool", layout="wide")
inject_css()

st.markdown('<div class="rv-title">Google Play Reviews Tool</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="rv-subtitle">Collect last N days of reviews across all storefronts (FULL mode). Merged into one table.</div>',
    unsafe_allow_html=True,
)
st.write("")

# Sidebar controls (cleaner main UI)
with st.sidebar:
    st.header("Controls")
    app_label = st.selectbox("App", list(APPS.keys()))
    days = st.number_input("Days back", min_value=1, max_value=30, value=7, step=1)
    st.divider()
    st.subheader("Filters")
    star_filter = st.multiselect("Stars", options=[1, 2, 3, 4, 5], default=[1, 2, 3, 4, 5])
    search_text = st.text_input("Search in Review Note / Reply", value="")
    st.caption("Tip: search keywords like “crash”, “language”, “Hindi”.")

package = APPS[app_label]

# Action row
action_col1, action_col2 = st.columns([1, 2])
with action_col1:
    fetch_clicked = st.button("Fetch reviews", type="primary")
# with action_col2:
#     st.markdown(
    #     '<div class="rv-card">This tool always runs <b>ALL Countries</b> using the full storefront list and merges results into one table. '
    #     'Rows are highlighted by Star rating.</div>',
        #unsafe_allow_html=True,
    #)

st.write("")

# Cache last results in session so filters don't refetch every time
if "rv_raw" not in st.session_state:
    st.session_state["rv_raw"] = pd.DataFrame()

if fetch_clicked:
    with st.spinner("Fetching ALL Countries reviews…"):
        raw = fetch_all_storefronts_full(package, int(days))
    st.session_state["rv_raw"] = raw

raw = st.session_state["rv_raw"]
df = format_for_ui(raw) if not raw.empty else pd.DataFrame()

# Metrics card (star counts only)
st.markdown('<div class="rv-card">', unsafe_allow_html=True)
st.subheader("Star counts")
counts = star_counts(df)
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("⭐ 1 Star", counts[1])
m2.metric("⭐ 2 Star", counts[2])
m3.metric("⭐ 3 Star", counts[3])
m4.metric("⭐ 4 Star", counts[4])
m5.metric("⭐ 5 Star", counts[5])
st.markdown("</div>", unsafe_allow_html=True)

st.write("")

# Apply filters (no refetch)
filtered = df.copy()

if not filtered.empty:
    if "Star" in filtered.columns and star_filter:
        filtered = filtered[filtered["Star"].isin(star_filter)]

    q = (search_text or "").strip().lower()
    if q:
        note = filtered.get("Review Note", pd.Series([""] * len(filtered))).fillna("").astype(str).str.lower()
        reply = filtered.get("Reply Message", pd.Series([""] * len(filtered))).fillna("").astype(str).str.lower()
        filtered = filtered[note.str.contains(re.escape(q), regex=True) | reply.str.contains(re.escape(q), regex=True)]

# Table section
st.markdown('<div class="rv-card">', unsafe_allow_html=True)
st.subheader("Merged reviews")

if df.empty:
    st.info("Click **Fetch reviews** to load reviews.")
else:
    st.caption(f"Showing {len(filtered)} of {len(df)} reviews after filters.")
    styled = style_by_star_background(filtered.style)

    st.dataframe(styled, use_container_width=True, height=650)

    # Download button uses the filtered view (more useful for teams)
    csv_bytes = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download CSV (filtered view)",
        data=csv_bytes,
        file_name="reviews_all_countries_filtered.csv",
        mime="text/csv",
    )

st.markdown("</div>", unsafe_allow_html=True)
