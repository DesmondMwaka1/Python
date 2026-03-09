import time
from matplotlib import pyplot as plt
import pandas as pd

#mergesort algo
def merge_sort(iter_list): 
    if len(iter_list) <= 1:
        return

    #Divide
    mid = len(iter_list) // 2
    left_iter = iter_list[:mid]
    right_iter = iter_list[mid:]
    
    merge_sort(left_iter)
    merge_sort(right_iter)
    
    #Merge 
    i = 0  
    j = 0 
    k = 0 
    
    while i < len(left_iter) and j < len(right_iter): 
        if left_iter[i] < right_iter[j]:
            iter_list[k] = left_iter[i]
            i += 1
        else:
            iter_list[k] = right_iter[j]
            j += 1
        k += 1
        
    # Append any remaining elements from the left list
    while i < len(left_iter):
        iter_list[k] = left_iter[i]
        i += 1
        k += 1
        
    # Append any remaining elements from the right list
    while j < len(right_iter):
        iter_list[k] = right_iter[j]
        j += 1
        k += 1
            

#get duration
def duration_fn(iter):
    n=len(iter)
    
    start=time.perf_counter()
    merge_sort(iter)
    stop=time.perf_counter()
      
    #saving duration and n to csv file    
    duration=stop-start
    
    data = {
        'n': [n],
        'time': [duration]
    }
    df = pd.DataFrame(data)
    try:
        df.to_csv('mergesort_duration.csv', mode='a', header=False,  index=False)  
        print("New data successfully added")

    except :
        print(f"An error occurred")
    
#visualize csv data
def visualize():
    #read stored data
    df=pd.read_csv(r"mergesort_duration.csv")

    x=df["n"]
    y=df["time"]
    #visualize
    plt.plot(x,y,marker='o')
    plt.title("Time Complexity of mergesort")
    plt.xlabel("n")
    plt.ylabel("time for exection")
    plt.show()

#sample data
ff=[
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

#get duration
for i in ff:
    duration_fn(i)

#visualize
visualize()