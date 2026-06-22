def fibonacci(num):
    if num <= 0:
        return 0
    if num == 1:
        return 1

    prev = 0
    curr = 1

    for _ in range(2, num + 1):
        nxt = prev + curr
        prev = curr
        curr = nxt
    return curr


def main():

    for k in range(10):
        print(k, fibonacci(k))


if __name__ == "__main__":
    main()
