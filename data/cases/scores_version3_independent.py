# scores_version3_independent.py
# Same statistical task but implemented in a more structured, different style.

from dataclasses import dataclass
from typing import List
import statistics


@dataclass
class ScoreSummary:
    count: int
    mean: float
    median: float
    min_value: float
    max_value: float
    variance: float


def summarize_scores(values: List[float]) -> ScoreSummary:
    if not values:
        raise ValueError("values must not be empty")

    # This implementation deliberately uses Python's statistics library
    # and avoids the explicit loops of the other versions.
    count = len(values)
    mean_val = statistics.fmean(values)
    median_val = statistics.median(values)
    min_val = min(values)
    max_val = max(values)

    if count > 1:
        variance_val = statistics.variance(values)
    else:
        variance_val = 0.0

    return ScoreSummary(
        count=count,
        mean=mean_val,
        median=median_val,
        min_value=min_val,
        max_value=max_val,
        variance=variance_val,
    )


def main():
    sample_scores = [88, 92, 76, 81, 95, 89, 73, 84, 90]

    summary = summarize_scores(sample_scores)

    print("Scores:", sample_scores)
    print("Count:", summary.count)
    print("Mean:", round(summary.mean, 2))
    print("Median:", summary.median)
    print("Min:", summary.min_value)
    print("Max:", summary.max_value)
    print("Variance:", round(summary.variance, 2))


if __name__ == "__main__":
    main()
