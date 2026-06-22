def sieve_of_eratosthenes(limit):
    """Find all primes up to limit using the Sieve of Eratosthenes."""
    if limit < 2:
        return []

    is_prime = [True] * (limit + 1)
    is_prime[0] = is_prime[1] = False

    for i in range(2, int(limit ** 0.5) + 1):
        if is_prime[i]:
            for j in range(i * i, limit + 1, i):
                is_prime[j] = False

    primes = [i for i, flag in enumerate(is_prime) if flag]
    return primes


def main():
    limits = [20, 50, 100]
    for lim in limits:
        primes = sieve_of_eratosthenes(lim)
        print(f"TrialDivision primes<={lim}: {primes}")


if __name__ == "__main__":
    main()
