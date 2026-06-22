import sys
from collections import Counter

def read_words():
    data = sys.stdin.read()
    for token in data.split():
        yield token.lower()

def main():
    counts = Counter(read_words())
    for word, cnt in sorted(counts.items()):
        print(word, cnt)


if __name__ == "__main__":
    main()
