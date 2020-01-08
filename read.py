import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

file_location = "/Users/puaqieshang/Desktop/Taste of Research/everything/inital_experiments/pua.csv"
df = pd.read_csv(file_location, header= None)
df = np.array(df)
print(df)