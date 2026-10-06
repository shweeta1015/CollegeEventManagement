"""
Keyword-Based Sentiment Categorization (Demonstration Module)
-------------------------------------------------------------
NOTE: This is a clearly labelled heuristic demonstration module for college ADBMS
project evaluation, NOT a machine learning or deep neural network sentiment model.
It scans feedback comments against curated positive and constructive/negative
dictionaries to classify feedback sentiment for event reporting.
"""

POSITIVE_KEYWORDS = {
    "great", "excellent", "awesome", "fantastic", "amazing", "good", "loved", 
    "helpful", "informative", "engaging", "enjoyed", "organized", "inspiring",
    "wonderful", "valuable", "clear", "brilliant", "superb", "interactive"
}

NEGATIVE_KEYWORDS = {
    "poor", "bad", "terrible", "horrible", "disorganized", "boring", "late", 
    "waste", "unprepared", "confusing", "crowded", "delayed", "useless", 
    "noisy", "rushed", "worst", "unclear", "disappointing"
}


def analyze_sentiment_demo(text):
    """
    Performs keyword frequency analysis to categorize feedback sentiment.
    Returns:
        dict: {
            "label": "Positive" | "Neutral" | "Constructive/Negative",
            "score": float (-1.0 to 1.0),
            "matched_positive": list of str,
            "matched_negative": list of str,
            "demo_notice": "Categorized via rule-based keyword analyzer (Demo mode)"
        }
    """
    if not text or not isinstance(text, str):
        return {
            "label": "Neutral",
            "score": 0.0,
            "matched_positive": [],
            "matched_negative": [],
            "demo_notice": "Categorized via rule-based keyword analyzer (Demo mode)"
        }

    words = text.lower().replace(".", " ").replace(",", " ").replace("!", " ").split()
    matched_pos = [w for w in words if w in POSITIVE_KEYWORDS]
    matched_neg = [w for w in words if w in NEGATIVE_KEYWORDS]

    pos_count = len(matched_pos)
    neg_count = len(matched_neg)

    if pos_count > neg_count:
        label = "Positive"
        score = min(1.0, 0.3 + (pos_count * 0.2))
    elif neg_count > pos_count:
        label = "Constructive/Negative"
        score = max(-1.0, -0.3 - (neg_count * 0.2))
    else:
        label = "Neutral"
        score = 0.0

    return {
        "label": label,
        "score": round(score, 2),
        "matched_positive": list(set(matched_pos)),
        "matched_negative": list(set(matched_neg)),
        "demo_notice": "Categorized via rule-based keyword analyzer (Demo mode)"
    }
