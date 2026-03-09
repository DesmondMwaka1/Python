import time
from matplotlib import pyplot as plt
import pandas as pd


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