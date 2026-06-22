def matrix_multiply(A, B):
    """Multiply two matrices by decomposing into vector dot products."""
    rows_A = len(A)
    cols_A = len(A[0])
    cols_B = len(B[0])

    # Transpose B for cache-friendly access pattern
    B_T = [[B[i][j] for i in range(len(B))] for j in range(cols_B)]

    result = []
    for i in range(rows_A):
        row = []
        for j in range(cols_B):
            # Compute dot product of A[i] and B_T[j]
            s = 0
            for k in range(cols_A):
                s += A[i][k] * B_T[j][k]
            row.append(s)
        result.append(row)

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
