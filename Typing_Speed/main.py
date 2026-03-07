import time

def start_typing_test():
    input("Press Enter to start the typing test...\n")
    start= time.time()
    text= input("Type the following text as fast as you can:\n\n")
    end= time.time()
    duration= end- start

    word_count = len(text.split())
    print(f"{word_count} words typed in {duration:.2f} seconds.")
    wpm= (word_count/ duration) 
    print(f"Your typing speed is {wpm} words per second.")

if __name__ == "__main__":
    start_typing_test()