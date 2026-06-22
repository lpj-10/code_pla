import sys
from collections import Counter

def collect_words():
    text = sys.stdin.read()
    tokens = text.split()
    return [t.lower() for t in tokens]

def main():
    freq = Counter(collect_words())
    for w in sorted(freq):
        print(w, freq[w])


if __name__ == "__main__":
    main()
