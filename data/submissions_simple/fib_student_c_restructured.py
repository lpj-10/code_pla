class FibSolver:
    def __init__(self):
        self.cache = {0: 0, 1: 1}

    def fib(self, n):
        if n in self.cache:
            return self.cache[n]

        a = self.cache[0]
        b = self.cache[1]
        k = 2
        while k <= n:
            a, b = b, a + b
            self.cache[k] = b
            k += 1
        return self.cache[n]


def main():
    solver = FibSolver()
    for i in range(10):
        print(i, solver.fib(i))


if __name__ == "__main__":
    main()
