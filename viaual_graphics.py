import pandas as pd
import matplotlib.pyplot as plt

data = pd.read_csv('graphics.csv')
plt.plot(data['x'], data['y'], marker='o')
plt.xlabel('X')
plt.ylabel('Y')
plt.title('Line Graph')
plt.show()