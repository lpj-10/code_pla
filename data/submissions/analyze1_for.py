GLOBAL_CONST = 42

def basic_test(a, b):
    c = a + b if a > b else a - b
    d = (a * b) + (GLOBAL_CONST - c)
    print("Basic:", d)
    return d


def loop_test():
    nums = [1, 2, 3, 4]
    total = 0
    # range
    for i in range(5):
        total += i
    # range(start, stop, step)
    for i in range(10, 0, -2):
        total += i
    # reversed(range)
    for i in reversed(range(3)):
        total += i
    # zip
    for a, b in zip(nums, range(4)):
        total += a * b
    # enumerate
    for idx, val in enumerate(nums):
        total += idx + val
    # dict.items
    d = {'x': 1, 'y': 2}
    for key, val in d.items():
        total += val
    print("Loop total:", total)
    return total


def control_flow_flatten(x):
    if x == 1:
        print("One")
    elif x == 2:
        print("Two")
    elif x == 3:
        print("Three")
    else:
        print("Other")
    return x * 2

class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

def test_match(obj):
    match obj:
        case 2 | 3:
            print("x is two or three")
        case Point(x=None, y=y):
            print(f"Point with x=None, y={y}")
        case int(x) if x > 10:
            print(f"Integer greater than 10: {x}")
        case [x, y, z]:
            if len([x, y, z]) == 3:
                print("Matched sequence [1,2,3]")
        case _:
            print("Default case")

def dead_code_test():
    x = 10
    if x > 5:
        print("Live branch")
    else:
        print("Dead branch")
    return x


def integrated_test():
    print("Start integrated test")
    v1 = basic_test(5, 3)
    v2 = loop_test()
    v3 = control_flow_flatten(3)
    test_match(Point(None, 2))
    test_match(3)
    test_match(15)
    test_match([1, 2, 3])
    v4 = dead_code_test()
    print(v1)

if __name__ == "__main__":
    integrated_test()