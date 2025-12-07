import time
from matplotlib import pyplot as plt

f=[
    [7],
    [4, 1], 
    [3, 0,1], 
    [1, 9,6,3], 
    [2, 5,3,2,1], 
    [10, 9,5,7,4,9], 
    [6, 4,7,8,3,0,1], 
    [3, 9, 9,3,2,7,0,3], 
    [5, 6, 9, 1,3,4,1,9,6], 
    [4, 10, 2, 8,3,4,6,2,8,0], 
    [1, 7, 8, 4,3,2,1,5,7,0,9,4], 
    [8, 10, 2, 7,2,6,8,0,3,1,5,6,8], 
    [7, 4, 10, 8, 9,2,1,5,7,9,4,6,7,4], 
    [2, 6, 3, 0, 5, 10,3,2,1,5,6,3,9,3,0]
]

def quicksort(iter):
    if len(iter)<=1:
        return iter
    else:
        pivot=iter.pop()
        
    items_less=[]
    items_greator=[]
    
    for item in iter:
        if(item<pivot):
            items_less.append(item)
        else:
            items_greator.append(item)
            
    return quicksort(items_less)+[pivot]+quicksort(items_greator)


def timer(lists):
    x=[]
    y=[]
    for i in lists:
        n=len(i)
        x.append(n)
        
        list_copy = i.copy()
        start=time.perf_counter()
        quicksort(list_copy)
        stop=time.perf_counter()
        
        duration=stop-start
        y.append(duration)
    return x,y


x,y=timer(f)
print(x)
print(y)


plt.plot(x,y)
plt.xlabel("n")
plt.ylabel("time complexity")
plt.show()
    