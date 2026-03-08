import time
import random
import textwrap

passages = [
    "The quick brown fox jumps over the lazy dog.",
    "A good programmer is someone who always looks both ways before crossing a one-way street.",
    "Typing tests measure speed in words per minute and accuracy."
]


def start_typing_test():
    """Run a short typing test using a random passage.

    Measures duration, words per minute (WPM), characters per minute (CPM),
    and reports character- and word-level accuracy plus a few mismatches.
    """
    print("Typing test — type the exact passage shown and press Enter when done.\n")
    passage = random.choice(passages)
    print("Passage to type:\n")
    print(textwrap.fill(passage, width=80))

    input("\nPress Enter to start...\n")
    start = time.perf_counter()
    typed = input()
    end = time.perf_counter()
    duration = end - start

    # Avoid division by zero for extremely fast/empty inputs
    if duration <= 0:
        duration = 0.01

    word_count = len(typed.split())
    wpm = (word_count / duration) * 60
    char_count = len(typed)
    cpm = (char_count / duration) * 60

    # Character-level accuracy against the target passage
    correct_chars = sum(1 for i, c in enumerate(typed) if i < len(passage) and c == passage[i])
    accuracy_chars = (correct_chars / len(passage)) * 100 if len(passage) else 0.0

    # Word-level accuracy
    typed_words = typed.split()
    target_words = passage.split()
    correct_words = sum(1 for i, w in enumerate(typed_words) if i < len(target_words) and w == target_words[i])
    accuracy_words = (correct_words / len(target_words)) * 100 if len(target_words) else 0.0

    print(f"\nTime: {duration:.2f} seconds")
    print(f"Words typed: {word_count}, WPM: {wpm:.2f}")
    print(f"Characters typed: {char_count}, CPM: {cpm:.0f}")
    print(f"Accuracy (chars): {accuracy_chars:.1f}%")
    print(f"Accuracy (words): {accuracy_words:.1f}%")

    if typed != passage:
        mismatches = []
        for i in range(min(len(typed), len(passage))):
            if typed[i] != passage[i]:
                mismatches.append((i, passage[i], typed[i]))
                if len(mismatches) >= 10:
                    break

        if mismatches:
            print("\nMistakes (index: expected -> got):")
            for idx, exp, got in mismatches:
                print(f"{idx}: {exp!r} -> {got!r}")

        if len(typed) != len(passage):
            print(f"...and length differs (expected {len(passage)} chars, got {len(typed)})")


if __name__ == "__main__":
    start_typing_test()