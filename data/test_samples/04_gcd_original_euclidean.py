def gcd(a, b):
    """Compute greatest common divisor using Euclidean algorithm."""
    while b != 0:
        a, b = b, a % b
    return abs(a)


def lcm(a, b):
    """Compute least common multiple."""
    return abs(a * b) // gcd(a, b)


def main():
    pairs = [(48, 18), (56, 98), (101, 103)]
    for a, b in pairs:
        g = gcd(a, b)
        l = lcm(a, b)
        print(f"EuclideanGCD({a},{b}) gcd={g} lcm={l}")


if __name__ == "__main__":
    main()
