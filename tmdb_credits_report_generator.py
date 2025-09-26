#!/usr/bin/env python3
"""
TMDB 5000 Credits — Report Generator (English)
Requires: pandas, matplotlib, numpy
Usage: python tmdb_credits_report_generator.py --csv tmdb_5000_credits.csv --out report.html
"""

import os, ast, json, io, base64, argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from collections import Counter

def safe_parse_list_of_dicts(value):
    if isinstance(value, list):
        return value
    if pd.isna(value):
        return []
    text = str(value).strip()
    if not text:
        return []
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, list):
            return parsed
    except Exception:
        try:
            parsed = json.loads(text.replace("'", '"'))
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
    return []

def extract_director(crew_list):
    for person in crew_list:
        job = person.get("job") if isinstance(person, dict) else None
        if job == "Director":
            return person.get("name")
    return None

def unique_names(list_of_dicts, key="name"):
    names = set()
    for d in list_of_dicts:
        if isinstance(d, dict):
            name = d.get(key)
            if isinstance(name, str) and name.strip():
                names.add(name.strip())
    return len(names)

def fig_to_base64():
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close()
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")

def iter_cast_genders(cast_list):
    for d in cast_list:
        if isinstance(d, dict):
            g = d.get("gender", 0)
            if g == 1:
                yield "Female"
            elif g == 2:
                yield "Male"
            else:
                yield "Unknown"

def main(args):
    csv_path = args.csv
    out_path = args.out

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    df.columns = [c.strip().lower() for c in df.columns]

    # Parse & engineer
    df["cast_parsed"] = df["cast"].apply(safe_parse_list_of_dicts)
    df["crew_parsed"] = df["crew"].apply(safe_parse_list_of_dicts)
    df["cast_size"] = df["cast_parsed"].apply(len)
    df["unique_cast_names"] = df["cast_parsed"].apply(unique_names)
    df["director_name"] = df["crew_parsed"].apply(extract_director)

    # Tables
    desc_stats = df[["cast_size", "unique_cast_names"]].describe().round(2)
    preview = df[["movie_id", "title", "cast_size", "unique_cast_names", "director_name"]].head(10)

    # Plots -> base64
    df["cast_size"].plot(kind="hist", bins=30)
    plt.title("Distribution of Cast Size")
    plt.xlabel("Cast Size")
    plt.ylabel("Frequency")
    img_hist_cast = fig_to_base64()

    df["unique_cast_names"].plot(kind="hist", bins=30)
    plt.title("Distribution of Unique Cast Names")
    plt.xlabel("Unique Cast Names")
    plt.ylabel("Frequency")
    img_hist_unique = fig_to_base64()

    top_directors = (
        df.dropna(subset=["director_name"])
          .groupby("director_name", as_index=False)["movie_id"]
          .count()
          .rename(columns={"movie_id": "movie_count"})
          .sort_values("movie_count", ascending=False)
          .head(15)
          .reset_index(drop=True)
    )

    plt.figure(figsize=(10,6))
    plt.bar(top_directors["director_name"], top_directors["movie_count"])
    plt.xticks(rotation=60, ha="right")
    plt.title("Top 15 Directors by Movie Count")
    plt.xlabel("Director")
    plt.ylabel("Movie Count")
    img_top_directors = fig_to_base64()

    gender_counter = Counter()
    for cast_list in df["cast_parsed"]:
        for g in iter_cast_genders(cast_list):
            gender_counter[g] += 1
    gender_df = pd.DataFrame(
        sorted(gender_counter.items(), key=lambda x: x[1], reverse=True),
        columns=["gender", "count"]
    )

    plt.figure()
    plt.bar(gender_df["gender"], gender_df["count"])
    plt.title("Cast Gender Distribution (All Credits)")
    plt.xlabel("Gender")
    plt.ylabel("Count")
    img_gender = fig_to_base64()

    # HTML
    html = f"""
<!doctype html>
<html lang='en'>
<head>
  <meta charset='utf-8'>
  <title>TMDB 5000 Credits — Data Analysis Report (EN)</title>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; margin: 32px; line-height: 1.6; }}
    h1, h2, h3 {{ margin-top: 1.4em; }}
    .note {{ background: #f7f7f7; border-left: 4px solid #999; padding: 10px 14px; }}
    img {{ max-width: 100%; height: auto; display:block; margin: 10px 0; }}
    table {{ border-collapse: collapse; width: 100%; margin: 8px 0; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background: #f0f0f0; }}
    code {{ background: #f6f6f6; padding: 2px 4px; border-radius: 3px; }}
  </style>
</head>
<body>
  <h1>TMDB 5000 Credits — Data Analysis Report</h1>

  <div class='note'>
    <strong>Dataset:</strong> <code>{os.path.basename(csv_path)}</code> • <strong>Entries:</strong> {len(df):,}
  </div>

  <h2>Introduction</h2>
  <p>This report analyzes TMDB movie credits (cast &amp; crew) to produce indicators such as cast size, unique cast names, and top directors. 
  This dataset does not include budget/revenue; if <code>tmdb_5000_movies.csv</code> is available, it can be merged via <code>movie_id</code> for deeper success analysis.</p>

  <h2>Questions</h2>
  <ul>
    <li>How is <em>cast size</em> distributed across movies?</li>
    <li>How many <em>unique cast names</em> are typically involved?</li>
    <li>Who are the most prolific directors in this sample?</li>
    <li>What does overall cast gender distribution look like (if provided)?</li>
  </ul>

  <h2>Data Wrangling</h2>
  <p>We safely parsed <code>cast</code> and <code>crew</code> JSON-like strings into Python lists of dicts, then engineered:</p>
  <ul>
    <li><code>cast_size</code>: list length of cast</li>
    <li><code>unique_cast_names</code>: number of distinct cast names</li>
    <li><code>director_name</code>: first crew member with job == "Director"</li>
  </ul>

  <h3>Sample Preview</h3>
  {preview.to_html(index=False)}

  <h3>Descriptive Statistics</h3>
  {desc_stats.to_html()}

  <h2>Exploratory Data Analysis</h2>

  <h3>Distribution of Cast Size</h3>
  <img src='data:image/png;base64,{img_hist_cast}' alt='Histogram cast size' />

  <h3>Distribution of Unique Cast Names</h3>
  <img src='data:image/png;base64,{img_hist_unique}' alt='Histogram unique cast names' />

  <h3>Top 15 Directors by Movie Count</h3>
  {top_directors.to_html(index=False)}
  <img src='data:image/png;base64,{img_top_directors}' alt='Top directors bar plot' />

  <h3>Cast Gender Distribution (All Credits)</h3>
  {gender_df.to_html(index=False)}
  <img src='data:image/png;base64,{img_gender}' alt='Gender distribution' />

  <h2>Conclusions</h2>
  <ul>
    <li>Cast size varies widely; most films cluster around mid-range with a long tail of large ensembles.</li>
    <li>Unique cast names track cast size as expected, with variability due to recurring names across films.</li>
    <li>A small subset of directors account for more titles in the sample.</li>
  </ul>

  <h2>Limitations & Next Steps</h2>
  <ul>
    <li>This file lacks outcome metrics (revenue/budget/ratings). For success drivers, merge <code>tmdb_5000_movies.csv</code> via <code>movie_id</code>.</li>
    <li>Explorations are descriptive; no causal claims are made.</li>
    <li>Future work: enrich with genres, runtime, popularity; build correlation/regression models.</li>
  </ul>

  <hr/>
  <p><em>Generated with Python (pandas + Matplotlib). Plots are embedded; this file is submission-ready.</em></p>
</body>
</html>
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=str, default="tmdb_5000_credits.csv", help="Path to tmdb_5000_credits.csv")
    parser.add_argument("--out", type=str, default="tmdb_credits_report_en.html", help="Output HTML path")
    args = parser.parse_args()
    main(args)
