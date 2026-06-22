def multiply_matrices(mat1, mat2):
    """Perform matrix multiplication using triple-nested loops."""
    m = len(mat1)
    n = len(mat1[0])
    p = len(mat2[0])

    # Initialize result matrix with zeros
    product = [[0 for _ in range(p)] for _ in range(m)]

    # Standard O(n^3) multiplication
    for r in range(m):
        for c in range(p):
            acc = 0
            for d in range(n):
                acc += mat1[r][d] * mat2[d][c]
            product[r][c] = acc

    return product


def display_matrix(mat):
    for row in mat:
        print(" ".join(f"{x:4d}" for x in row))


def main():
    A = [[1, 2, 3], [4, 5, 6]]
    B = [[7, 8], [9, 10], [11, 12]]
    result = multiply_matrices(A, B)
    print("MatMul result A*B:")
    display_matrix(result)


if __name__ == "__main__":
    main()
