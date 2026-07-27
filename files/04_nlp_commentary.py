"""
Aurora Dynamics FP&A — NLP Analysis of Management Commentary
===============================================================
No internet access in this environment, so this uses a self-contained
lexicon-based sentiment scorer (no NLTK/VADER download required) plus
TF-IDF keyword extraction and KMeans topic clustering from scikit-learn.

Outputs:
- commentary_nlp_scored.csv   (per-comment sentiment score + label + top keywords)
- commentary_topic_clusters.csv
- commentary_vs_variance_link.csv  (ties qualitative tone to quantitative opex variance)
"""
import sqlite3
import re
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

DB_PATH = "/home/claude/fpa_project/data/aurora_fpa.db"
OUT_DIR = "/home/claude/fpa_project/data"

conn = sqlite3.connect(DB_PATH)
commentary = pd.read_sql("SELECT * FROM fact_management_commentary", conn)
cost_centers = pd.read_sql("SELECT * FROM dim_cost_centers", conn)

# ------------------------------------------------------------------
# 1. LEXICON-BASED SENTIMENT SCORER
# ------------------------------------------------------------------
POSITIVE_WORDS = {
    "exceeded", "strong", "accelerated", "improved", "improvement", "ahead", "growth",
    "grew", "success", "successfully", "reduction", "reduced", "expansion", "notable",
    "solid", "meaningful", "outperform", "beat", "healthy", "efficient", "optimization",
    "increased", "gains", "positive", "record",
}
NEGATIVE_WORDS = {
    "slipped", "delay", "delayed", "elevated", "attrition", "pressure", "pressured",
    "exceeded plan", "softened", "churn", "dispute", "unplanned", "freeze", "freezes",
    "slowdown", "risk", "miss", "missed", "shortfall", "decline", "declined", "concern",
    "concerns", "challenge", "challenges", "over budget", "overrun", "weak", "weakness",
}
NEGATION_WORDS = {"not", "no", "without", "never"}

def score_sentiment(text: str):
    tokens = re.findall(r"[a-zA-Z']+", text.lower())
    pos_hits, neg_hits = 0, 0
    for i, tok in enumerate(tokens):
        preceding = tokens[max(0, i - 2):i]
        negated = any(w in NEGATION_WORDS for w in preceding)
        if tok in POSITIVE_WORDS:
            neg_hits += 1 if negated else 0
            pos_hits += 0 if negated else 1
        elif tok in NEGATIVE_WORDS:
            pos_hits += 1 if negated else 0
            neg_hits += 0 if negated else 1
    total_hits = pos_hits + neg_hits
    score = (pos_hits - neg_hits) / total_hits if total_hits > 0 else 0.0
    if score > 0.2:
        label = "Positive"
    elif score < -0.2:
        label = "Negative"
    else:
        label = "Neutral"
    return pd.Series({"sentiment_score": round(score, 3), "predicted_tone": label,
                       "positive_hits": pos_hits, "negative_hits": neg_hits})

commentary = commentary.join(commentary["commentary_text"].apply(score_sentiment))

# Accuracy of the lexicon scorer vs. the (ground-truth) authored tone label
commentary["match_authored_label"] = (
    commentary["predicted_tone"].str.lower() == commentary["authored_tone_label"].str.lower()
)
accuracy = commentary["match_authored_label"].mean()

# ------------------------------------------------------------------
# 2. TF-IDF KEYWORD EXTRACTION (top terms per comment)
# ------------------------------------------------------------------
vectorizer = TfidfVectorizer(stop_words="english", max_features=200, ngram_range=(1, 2))
tfidf_matrix = vectorizer.fit_transform(commentary["commentary_text"])
feature_names = np.array(vectorizer.get_feature_names_out())

top_keywords = []
for row in tfidf_matrix:
    row_arr = row.toarray().flatten()
    top_idx = row_arr.argsort()[-5:][::-1]
    top_idx = [i for i in top_idx if row_arr[i] > 0]
    top_keywords.append(", ".join(feature_names[top_idx]))
commentary["top_keywords"] = top_keywords

# ------------------------------------------------------------------
# 3. TOPIC CLUSTERING (KMeans over TF-IDF space) — unsupervised theme discovery
# ------------------------------------------------------------------
n_clusters = 5
km = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
commentary["topic_cluster"] = km.fit_predict(tfidf_matrix)

cluster_terms = {}
order_centroids = km.cluster_centers_.argsort()[:, ::-1]
for i in range(n_clusters):
    top_terms = [feature_names[ind] for ind in order_centroids[i, :6]]
    cluster_terms[i] = ", ".join(top_terms)
commentary["topic_cluster_label"] = commentary["topic_cluster"].map(cluster_terms)

commentary = commentary.merge(cost_centers, on="cost_center", how="left")
commentary.to_csv(f"{OUT_DIR}/commentary_nlp_scored.csv", index=False)

cluster_summary = (commentary.groupby(["topic_cluster", "topic_cluster_label"])
                    .agg(comment_count=("commentary_text", "count"),
                         avg_sentiment=("sentiment_score", "mean"))
                    .reset_index())
cluster_summary.to_csv(f"{OUT_DIR}/commentary_topic_clusters.csv", index=False)

# ------------------------------------------------------------------
# 4. LINK QUALITATIVE TONE TO QUANTITATIVE VARIANCE
# For each cost center + quarter, compare average commentary sentiment to
# actual opex variance vs. budget in that quarter — validating whether
# management narrative is a leading/coincident indicator of financial performance.
# ------------------------------------------------------------------
var_budget = pd.read_csv(f"{OUT_DIR}/variance_actual_vs_budget.csv", parse_dates=["period"])
var_budget_opex = var_budget[var_budget["line_type"] == "Opex"].copy()
var_budget_opex["fiscal_quarter"] = (var_budget_opex["period"].dt.year.astype(str) + "-Q" +
                                       ((var_budget_opex["period"].dt.month - 1) // 3 + 1).astype(str))
var_budget_opex.rename(columns={"dim1": "cost_center"}, inplace=True)

quarterly_var = (var_budget_opex.groupby(["fiscal_quarter", "cost_center"])
                  .agg(budget_amount=("budget_amount", "sum"), actual_amount=("actual_amount", "sum"))
                  .reset_index())
quarterly_var["variance_pct"] = ((quarterly_var["actual_amount"] - quarterly_var["budget_amount"])
                                   / quarterly_var["budget_amount"])

commentary["fiscal_quarter_norm"] = commentary["fiscal_quarter"].str.replace("-Q", "Q").str.replace("Q", "-Q")
quarterly_sentiment = (commentary.groupby(["fiscal_quarter", "cost_center"])
                        .agg(avg_sentiment=("sentiment_score", "mean"),
                             predicted_tone_mode=("predicted_tone", lambda x: x.mode()[0] if len(x.mode()) else None))
                        .reset_index())

link_df = quarterly_sentiment.merge(quarterly_var, on=["fiscal_quarter", "cost_center"], how="inner")
link_df.to_csv(f"{OUT_DIR}/commentary_vs_variance_link.csv", index=False)

corr = link_df[["avg_sentiment", "variance_pct"]].corr().iloc[0, 1] if len(link_df) > 2 else float("nan")

conn.close()

print("=== NLP Commentary Analysis complete ===")
print(f"Lexicon-sentiment agreement with authored tone label: {accuracy:.1%}")
print(f"\nTopic clusters discovered:")
print(cluster_summary.to_string(index=False))
print(f"\nCorrelation (commentary sentiment vs. opex variance % , negative overspend = negative sentiment expected): {corr:.3f}")
print(f"\nOutputs written to {OUT_DIR}/")
