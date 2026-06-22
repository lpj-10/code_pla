def gcd_stein(a, b):
    """Compute greatest common divisor using Stein's binary algorithm."""
    a, b = abs(a), abs(b)

    if a == 0:
        return b
    if b == 0:
        return a

    # Find the largest power of 2 dividing both a and b
    shift = 0
    while ((a | b) & 1) == 0:
        a >>= 1
        b >>= 1
        shift += 1

    # Make a odd
    while (a & 1) == 0:
        a >>= 1

    while b != 0:
        # Make b odd
        while (b & 1) == 0:
            b >>= 1

        if a > b:
            a, b = b, a
        b = b - a

    return a << shift


def lcm(a, b):
    """Compute least common multiple."""
    return abs(a * b) // gcd_stein(a, b)


def main():
    pairs = [(48, 18), (56, 98), (101, 103)]
    for a, b in pairs:
        g = gcd_stein(a, b)
        l = lcm(a, b)
        print(f"EuclideanGCD({a},{b}) gcd={g} lcm={l}")


if __name__ == "__main__":
    main()
