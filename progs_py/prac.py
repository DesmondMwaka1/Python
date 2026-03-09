def swapper(a,b):
    print(f"Before swapping: a={a} and b={b}")
    temp=a
    a=b
    b=temp
    print(f"After swapping: a={a} and b={b}.")
    
swapper(4,5)

def track(n):
    for i in range(n):
        print(f"When outer loop i={i}")
        print(f"inner loop:")
        for j in range(i):
            print(f"j={j}")

track(5)