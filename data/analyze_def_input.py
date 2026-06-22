def process(values):
    s = sum(values)
    avg = s / len(values)
    print("Average:", avg)
    return avg

def report(name, score):
    if score >= 60:
        print(f"{name} passed")
    else:
        print(f"{name} failed")

report("Bob", 75)
report("Lucy", 55)
process([1, 2, 3, 4, 5])
