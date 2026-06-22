def matmul_recursive(A, B):
    """Multiply two matrices using a recursive divide-and-conquer approach."""
    n = len(A)
    size = 1
    while size < n:
        size <<= 1

    def pad_matrix(M, size):
        result = [[0] * size for _ in range(size)]
        for i in range(len(M)):
            for j in range(len(M[0])):
                result[i][j] = M[i][j]
        return result

    A_pad = pad_matrix(A, size)
    B_pad = pad_matrix(B, size)

    def add(X, Y):
        return [[X[i][j] + Y[i][j] for j in range(len(X))] for i in range(len(X))]

    def sub(X, Y):
        return [[X[i][j] - Y[i][j] for j in range(len(X))] for i in range(len(X))]

    def strassen_mul(X, Y, size):
        if size <= 2:
            result = [[0] * size for _ in range(size)]
            for i in range(size):
                for j in range(size):
                    for k in range(size):
                        result[i][j] += X[i][k] * Y[k][j]
            return result

        mid = size // 2
        A11 = [row[:mid] for row in X[:mid]]
        A12 = [row[mid:] for row in X[:mid]]
        A21 = [row[:mid] for row in X[mid:]]
        A22 = [row[mid:] for row in X[mid:]]
        B11 = [row[:mid] for row in Y[:mid]]
        B12 = [row[mid:] for row in Y[:mid]]
        B21 = [row[:mid] for row in Y[mid:]]
        B22 = [row[mid:] for row in Y[mid:]]

        M1 = strassen_mul(add(A11, A22), add(B11, B22), mid)
        M2 = strassen_mul(add(A21, A22), B11, mid)
        M3 = strassen_mul(A11, sub(B12, B22), mid)
        M4 = strassen_mul(A22, sub(B21, B11), mid)
        M5 = strassen_mul(add(A11, A12), B22, mid)
        M6 = strassen_mul(sub(A21, A11), add(B11, B12), mid)
        M7 = strassen_mul(sub(A12, A22), add(B21, B22), mid)

        C11 = add(sub(add(M1, M4), M5), M7)
        C12 = add(M3, M5)
        C21 = add(M2, M4)
        C22 = add(sub(add(M1, M3), M2), M6)

        result = [[0] * size for _ in range(size)]
        for i in range(mid):
            for j in range(mid):
                result[i][j] = C11[i][j]
                result[i][j + mid] = C12[i][j]
                result[i + mid][j] = C21[i][j]
                result[i + mid][j + mid] = C22[i][j]
        return result

    full = strassen_mul(A_pad, B_pad, size)
    return [row[:len(B[0])] for row in full[:len(A)]]


def main():
    A = [[1, 2, 3], [4, 5, 6]]
    B = [[7, 8], [9, 10], [11, 12]]
    result = matmul_recursive(A, B)
    print("RecursiveMatMul result A*B:")
    for row in result:
        line = "  ".join(str(x) for x in row)
        print(f"  [{line}]")


if __name__ == "__main__":
    main()
