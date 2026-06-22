import math

def compute_average(scores):
    total = 0
    for s in scores:
        total += s
    return total / len(scores)

def grade_students(students):
    results = []
    for name, scores in students.items():
        avg = compute_average(scores)
        if avg >= 90:
            level = "A"
        elif avg >= 75:
            level = "B"
        elif avg >= 60:
            level = "C"
        else:
            level = "D"
        results.append((name, level, avg))
    return results

def display_report(data):
    print("=== Student Report ===")
    for name, level, avg in data:
        print(f"{name}: {avg:.2f} ({level})")
    print("======================")

students = {
    "Alice": [90, 92, 85],
    "Bob": [70, 65, 68],
    "Charlie": [88, 94, 91],
    "Daisy": [55, 58, 60],
}

report = grade_students(students)
display_report(report)

