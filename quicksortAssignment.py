import time
from matplotlib import pyplot as plt
import pandas as pd

#the quicksort algo
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

#list example
vals=[1,0,5,2,3,9,5,4,6]
n=len(vals)

#duration
start=time.perf_counter()
quicksort(vals)
stop=time.perf_counter()
        
duration=stop-start


#saving duration and n to csv file
data = {
    'n': [n],
    'time': [duration]
}

df = pd.DataFrame(data)

try:
    df.to_csv('duration.csv', mode='a', header=False,  index=False)  
    print("New data successfully added")

except :
    print(f"An error occurred")

#read stored data
df=pd.read_csv(r"duration.csv")

x=df["n"]
y=df["time"]

#visualize
plt.plot(x,y,marker='o')
plt.title("Time Complexity of Quicksort")
plt.xlabel("n")
plt.ylabel("time for exection")
plt.show()