def bubble_sort(arr):
    """Sort a list using bubble sort algorithm."""
    n = len(arr)
    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        if not swapped:
            break
    return arr


def main():
    test_arrays = [
        [64, 34, 25, 12, 22, 11, 90],
        [5, 1, 4, 2, 8],
    ]
    for arr in test_arrays:
        sorted_arr = bubble_sort(arr)
        print(f"BubbleSort input={arr} output={sorted_arr}")


if __name__ == "__main__":
    main()
