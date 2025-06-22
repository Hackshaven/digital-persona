def raw_to_normalized(score, min_score=0, max_score=100):
    """Convert raw score (e.g., percentile or raw inventory sum) to normalized 0.0–1.0."""
    if score < min_score or score > max_score:
        raise ValueError("Score out of bounds")
    return round((score - min_score) / (max_score - min_score), 4)


def normalized_to_percentile(norm_score):
    """Convert a normalized 0.0–1.0 score to a percentile (0–100)."""
    if norm_score < 0.0 or norm_score > 1.0:
        raise ValueError("Normalized score out of bounds")
    return int(round(norm_score * 100))


def map_all_traits(raw_scores_dict, min_score=0, max_score=100):
    """Apply normalization to a full dict of raw scores."""
    return {
        trait: raw_to_normalized(score, min_score, max_score)
        for trait, score in raw_scores_dict.items()
    }