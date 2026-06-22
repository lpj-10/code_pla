def sort_bubble(lst):
    """Arrange a list using bubble sorting method."""
    length = len(lst)
    for idx in range(length):
        has_swapped = False
        for jdx in range(0, length - idx - 1):
            if lst[jdx] > lst[jdx + 1]:
                lst[jdx], lst[jdx + 1] = lst[jdx + 1], lst[jdx]
                has_swapped = True
        if not has_swapped:
            break
    return lst


def main():
    test_arrays = [
        [64, 34, 25, 12, 22, 11, 90],
        [5, 1, 4, 2, 8],
    ]
    for arr in test_arrays:
        sorted_arr = sort_bubble(arr)
        print(f"BubbleSort input={arr} output={sorted_arr}")


if __name__ == "__main__":
    main()
