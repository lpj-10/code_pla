def binary_search(arr, target):
    """Search for target in sorted array using iterative binary search."""
    left = 0
    right = len(arr) - 1

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
        result = binary_search(data, target)
        if result != -1:
            print(f"BinarySearch found {target} at idx={result}")
        else:
            print(f"BinarySearch: {target} not found")


if __name__ == "__main__":
    main()
