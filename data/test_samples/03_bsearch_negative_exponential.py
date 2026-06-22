def exponential_search(arr, target):
    """Search for target using exponential search + binary search."""
    n = len(arr)
    if n == 0:
        return -1

    # Find range for binary search by repeated doubling
    bound = 1
    while bound < n and arr[bound] < target:
        bound *= 2

    # Do binary search in the found range
    left = bound // 2
    right = min(bound, n - 1)

    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1

    return -1


def main():
    data = [2, 5, 8, 12, 16, 23, 38, 45, 56, 72]
    for target in [23, 100, 5]:
        result = exponential_search(data, target)
        if result != -1:
            print(f"BinarySearch found {target} at idx={result}")
        else:
            print(f"BinarySearch: {target} not found")


if __name__ == "__main__":
    main()
