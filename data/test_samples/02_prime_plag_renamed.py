def check_prime(number):
    """Verify if a number is a prime by trial division."""
    if number <= 1:
        return False
    if number <= 3:
        return True
    if number % 2 == 0 or number % 3 == 0:
        return False

    divisor = 5
    while divisor * divisor <= number:
        if number % divisor == 0 or number % (divisor + 2) == 0:
            return False
        divisor += 6

    return True


def get_primes(max_val):
    """Collect all primes up to a maximum value."""
    primes = []
    for k in range(2, max_val + 1):
        if check_prime(k):
            primes.append(k)
    return primes


def main():
    limits = [20, 50, 100]
    for lim in limits:
        primes = get_primes(lim)
        print(f"TrialDivision primes<={lim}: {primes}")


if __name__ == "__main__":
    main()
