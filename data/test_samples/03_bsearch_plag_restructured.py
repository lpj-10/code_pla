def binary_search(arr, target):
    """Search for target in sorted array using recursive binary search."""

    def search_in_range(lo, hi):
        if lo > hi:
            return -1
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        if arr[mid] < target:
            return search_in_range(mid + 1, hi)
        else:
            return search_in_range(lo, mid - 1)

    return search_in_range(0, len(arr) - 1)


def main():
    data = [2, 5, 8, 12, 16, 23, 38, 45, 56, 72]
    for target in [23, 100, 5]:
        result = binary_search(data, target)
        if result != -1:
            print(f"BinarySearch found {target} at idx={result}")
        else:
            print(f"BinarySearch: {target} not found")


if __name__ == "__main__":
    main()
