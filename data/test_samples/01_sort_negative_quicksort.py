def quick_sort(arr):
    """Sort a list using quick sort algorithm."""
    if len(arr) <= 1:
        return arr

    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]

    return quick_sort(left) + middle + quick_sort(right)


def main():
    test_arrays = [
        [64, 34, 25, 12, 22, 11, 90],
        [5, 1, 4, 2, 8],
    ]
    for arr in test_arrays:
        sorted_arr = quick_sort(arr)
        print(f"BubbleSort input={arr} output={sorted_arr}")


if __name__ == "__main__":
    main()
