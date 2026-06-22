def is_prime(n):
    """Check if a number is prime using trial division."""
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False

    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6

    return True


def find_primes(limit):
    """Return all primes up to limit."""
    result = []
    for num in range(2, limit + 1):
        if is_prime(num):
            result.append(num)
    return result


def main():
    limits = [20, 50, 100]
    for lim in limits:
        primes = find_primes(lim)
        print(f"TrialDivision primes<={lim}: {primes}")


if __name__ == "__main__":
    main()
