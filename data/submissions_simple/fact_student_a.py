def fact(n):
    if n < 0:
        raise ValueError("negative not allowed")
    result = 1
    for k in range(2, n + 1):
        result *= k
    return result


def main():
    for i in range(10):
        print(i, fact(i))


if __name__ == "__main__":
    main()
