# scores_version1.py
# Simple script to compute basic statistics on a list of scores.

def compute_stats(scores):
    n = len(scores)
    if n == 0:
        raise ValueError("scores list is empty")

    # Sort once for median and sanity checks
    sorted_scores = sorted(scores)

    # Mean
    total = 0.0
    for s in scores:
        total += s
    mean = total / n

    # Median
    mid = n // 2
    if n % 2 == 1:
        median = sorted_scores[mid]
    else:
        median = (sorted_scores[mid - 1] + sorted_scores[mid]) / 2.0

    # Min and max
    min_val = sorted_scores[0]
    max_val = sorted_scores[-1]

    # Sample variance (unbiased, denominator n - 1 when n > 1)
    if n > 1:
        sq_diff_sum = 0.0
        for s in scores:
            diff = s - mean
            sq_diff_sum += diff * diff
        variance = sq_diff_sum / (n - 1)
    else:
        variance = 0.0

    return {
        "count": n,
        "mean": mean,
        "median": median,
        "min": min_val,
        "max": max_val,
        "variance": variance,
    }


def main():
    # Example data
    scores = [88, 92, 76, 81, 95, 89, 73, 84, 90]

    stats = compute_stats(scores)

    print("Scores:", scores)
    print("Count:", stats["count"])
    print("Mean:", round(stats["mean"], 2))
    print("Median:", stats["median"])
    print("Min:", stats["min"])
    print("Max:", stats["max"])
    print("Variance:", round(stats["variance"], 2))


if __name__ == "__main__":
    main()
