def is_prime(n):
    """Check if a number is prime using trial division."""
    if n <= 1:
        return False

    small_primes = [2, 3]
    for p in small_primes:
        if n == p:
            return True
        if n % p == 0:
            return False

    # 6k +/- 1 optimization
    def check_divisor(k):
        return n % k != 0 and n % (k + 2) != 0

    k = 5
    while k * k <= n:
        if not check_divisor(k):
            return False
        k += 6

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
