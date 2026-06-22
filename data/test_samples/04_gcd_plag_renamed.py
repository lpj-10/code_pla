def greatest_common_divisor(num1, num2):
    """Calculate greatest common divisor via Euclidean algorithm."""
    while num2 != 0:
        num1, num2 = num2, num1 % num2
    return abs(num1)


def least_common_multiple(num1, num2):
    """Calculate least common multiple."""
    return abs(num1 * num2) // greatest_common_divisor(num1, num2)


def main():
    pairs = [(48, 18), (56, 98), (101, 103)]
    for a, b in pairs:
        g = greatest_common_divisor(a, b)
        l = least_common_multiple(a, b)
        print(f"EuclideanGCD({a},{b}) gcd={g} lcm={l}")


if __name__ == "__main__":
    main()
