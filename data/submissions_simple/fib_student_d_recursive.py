def fib_recursive(n, memo=None):
    if memo is None:
        memo = {0: 0, 1: 1}
    if n in memo:
        return memo[n]
    memo[n] = fib_recursive(n - 1, memo) + fib_recursive(n - 2, memo)
    return memo[n]


def main():
    for i in range(10):
        print(i, fib_recursive(i))


if __name__ == "__main__":
    main()
