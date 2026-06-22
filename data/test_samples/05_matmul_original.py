def matrix_multiply(A, B):
    """Multiply two matrices using the standard triple-loop algorithm."""
    rows_A = len(A)
    cols_A = len(A[0])
    cols_B = len(B[0])

    result = [[0 for _ in range(cols_B)] for _ in range(rows_A)]

    for i in range(rows_A):
        for j in range(cols_B):
            for k in range(cols_A):
                result[i][j] += A[i][k] * B[k][j]

    return result


def print_matrix(mat):
    for row in mat:
        print(" ".join(f"{x:4d}" for x in row))


def main():
    A = [[1, 2, 3], [4, 5, 6]]
    B = [[7, 8], [9, 10], [11, 12]]
    result = matrix_multiply(A, B)
    print("MatMul result A*B:")
    print_matrix(result)


if __name__ == "__main__":
    main()
