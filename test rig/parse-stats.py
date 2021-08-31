#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse, os
import time
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

from pprint import pprint

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Process VE.Direct protocol')
	parser.add_argument('filename', help='Name of CSV file to parse')
	args = parser.parse_args()

	dtype = {'Time': np.float64, 'Efficiency' : np.float64}
	df = pd.read_csv(args.filename, dtype = dtype)

	pd.set_option('display.max_columns', None)
	pd.set_option('display.max_rows', None)
	
	pprint(df.head())
	
	#sns.lineplot(x = df['Time'], y = df['Gen Wattage'], data = df)

	t = df['Time']

	fig, axs = plt.subplots(2, 1)
	axs[0].plot(t, df['Gen Wattage'], t, df['Driver Wattage'])
	axs[0].set_xlabel('Time')
	axs[0].set_ylabel('Generated Wattage + Drive Wattage')
	axs[0].grid(True)

	axs[0].plot(t, df['Gen Wattage'], t, df['Driver Wattage'])
	axs[0].set_xlabel('Time')
	axs[0].set_ylabel('Generated Wattage + Drive Wattage')
	#axs[0].grid(True)

	axs[1].plot(t, df['Efficiency'])
	axs[1].set_xlabel('Time')
	axs[1].set_ylabel('Efficiency')
	#axs[1].grid(True)

	#sns.displot(df['Gen Wattage'])
	#plt.title('Brake Current vs. Wattage')
	#plt.ylabel('Wattage')
	#plt.xlabel('Current')

	fig.tight_layout()
	plt.show()
