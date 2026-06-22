def bin_search(xs, key):
    """Look for key in sorted array using iterative binary search."""
    lo = 0
    hi = len(xs) - 1

    while lo <= hi:
        center = (lo + hi) // 2
        if xs[center] == key:
            return center
        elif xs[center] < key:
            lo = center + 1
        else:
            hi = center - 1

    return -1


def main():
    data = [2, 5, 8, 12, 16, 23, 38, 45, 56, 72]
    for target in [23, 100, 5]:
        result = bin_search(data, target)
        if result != -1:
            print(f"BinarySearch found {target} at idx={result}")
        else:
            print(f"BinarySearch: {target} not found")


if __name__ == "__main__":
    main()
