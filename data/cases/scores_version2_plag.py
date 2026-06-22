# scores_version2_plag.py
# Very similar logic to scores_version1.py, with only light renaming and reordering.

def stats_on_marks(marks):
    length = len(marks)
    if length == 0:
        raise ValueError("marks list is empty")

    ordered = sorted(marks)

    # Mean
    running_sum = 0.0
    for value in marks:
        running_sum += value
    avg = running_sum / length

    # Median (same algorithm as version1, just renamed)
    middle = length // 2
    if length % 2 == 1:
        mid_val = ordered[middle]
    else:
        mid_val = (ordered[middle - 1] + ordered[middle]) / 2.0

    # Extremes
    smallest = ordered[0]
    largest = ordered[-1]

    # Sample variance
    if length > 1:
        sq_acc = 0.0
        for value in marks:
            diff_val = value - avg
            sq_acc += diff_val * diff_val
        var = sq_acc / (length - 1)
    else:
        var = 0.0

    return {
        "count": length,
        "mean": avg,
        "median": mid_val,
        "min": smallest,
        "max": largest,
        "variance": var,
    }


def main():
    # Same data but with a tiny permutation
    marks = [92, 88, 76, 81, 95, 89, 73, 84, 90]

    result = stats_on_marks(marks)

    print("Marks:", marks)
    print("Count:", result["count"])
    print("Mean:", round(result["mean"], 2))
    print("Median:", result["median"])
    print("Min:", result["min"])
    print("Max:", result["max"])
    print("Variance:", round(result["variance"], 2))


if __name__ == "__main__":
    main()
