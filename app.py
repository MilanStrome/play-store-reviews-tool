import re
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, parse_qs
from google_play_scraper import reviews, Sort


def package_from_url(play_url: str) -> str:
    qs = parse_qs(urlparse(play_url).query)
    if "id" in qs and qs["id"]:
        return qs["id"][0]
    m = re.search(r"[?&]id=([^&]+)", play_url)
    if m:
        return m.group(1)
    raise ValueError("Could not find package id in URL (expected ?id=com.example.app)")


def to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def fetch_last_days(package_name: str, days: int, lang: str, country: str, max_pages: int = 50):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    all_rows = []
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

            all_rows.append(
                {
                    "reviewId": r.get("reviewId"),
                    "userName": r.get("userName"),
                    "score": r.get("score"),
                    "thumbsUpCount": r.get("thumbsUpCount"),
                    "reviewCreatedVersion": r.get("reviewCreatedVersion"),
                    "at_utc": at.isoformat(),
                    "content": r.get("content"),
                    "replyContent": r.get("replyContent") or "",
                    "repliedAt_utc": (to_utc(r["repliedAt"]).isoformat() if r.get("repliedAt") else ""),
                }
            )

        if stop or token is None:
            break

    df = pd.DataFrame(all_rows)
    if not df.empty:
        df = df.sort_values("at_utc", ascending=False)
    return df


st.set_page_config(page_title="Play Store Review Collector", layout="wide")
st.title("Google Play Reviews Collector (Last N Days)")

default_url = "https://play.google.com/store/apps/details?id=com.rvappstudios.abc_kids_toddler_tracing_phonics&hl=en"
url = st.text_input("Google Play app URL", value=default_url)
days = st.number_input("Days back", min_value=1, max_value=30, value=7, step=1)

col1, col2 = st.columns(2)
with col1:
    lang = st.text_input("Language (best-effort)", value="en")
with col2:
    country = st.text_input("Country storefront (best-effort)", value="us")

if st.button("Fetch reviews"):
    try:
        package = package_from_url(url)
        st.write(f"Package: `{package}`")

        with st.spinner("Fetching reviews..."):
            df = fetch_last_days(package, int(days), lang.strip(), country.strip())

        st.success(f"Collected {len(df)} reviews from the last {days} days.")
        st.dataframe(df, use_container_width=True)

        csv_bytes = df.to_csv(index=False).encode("utf-8")
        json_bytes = df.to_json(orient="records", force_ascii=False, indent=2).encode("utf-8")

        st.download_button("Download CSV", data=csv_bytes, file_name="reviews_last_days.csv", mime="text/csv")
        st.download_button("Download JSON", data=json_bytes, file_name="reviews_last_days.json", mime="application/json")

    except Exception as e:
        st.error(str(e))
