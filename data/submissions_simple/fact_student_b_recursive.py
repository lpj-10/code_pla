def fact_recursive(n):
    if n < 0:
        raise ValueError("negative not allowed")
    if n in (0, 1):
        return 1
    return n * fact_recursive(n - 1)


def main():
    for i in range(10):
        print(i, fact_recursive(i))


if __name__ == "__main__":
    main()
