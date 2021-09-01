#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse, os
import time
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import seaborn as sns
import numpy as np

from pprint import pprint

def plot_voltage(df):
	t = df['Time']
	fig, axs = plt.subplots()

	axs.plot(t, df['Driver Voltage'], label="Driver")
	axs.plot(t, df['Gen Voltage'], label="Generator")
	axs.set(title='Voltage', xlabel="Time", ylabel="Voltage")
	axs.legend()
	axs.grid(True)

	fig.savefig("graphs/vesc_voltage.png", dpi=200)

def plot_wattage(df):
	t = df['Time']
	fig, ax1 = plt.subplots()

	ax1.plot(t, df['Driver Wattage'], label="Driver", linewidth=1)
	ax1.plot(t, df['Gen Wattage'], label="Generator", linewidth=1)
	ax1.set(title='Power Consumed vs. Generated', xlabel="Time", ylabel="Wattage")
	ax1.legend(loc='lower right')
	
	color = 'tab:red'
	ax2 = ax1.twinx()
	ax2.plot(t, df['Efficiency'], label="Efficiency", color=color)
	ax2.set_ylabel('Efficiency (%)', color=color)
	ax2.tick_params(axis='y', labelcolor=color)
	
	fig.savefig("graphs/vesc_wattage.png", dpi=200)

def plot_brake_current_vs_wattage(df):
	t = df['Time']
	fig, ax1 = plt.subplots()

	ax1.set(title='Brake Current vs. Wattage', xlabel="Time", ylabel="Wattage")
	ax1.plot(t, df['Gen Wattage'], label="Generator Wattage")
	
	color = 'tab:red'
	ax2 = ax1.twinx()
	ax2.plot(t, df['Brake Current'], label="Brake Current", color=color)
	ax2.set_ylabel('Brake Current', color=color)
	ax2.tick_params(axis='y', labelcolor=color)
	
	fig.savefig("graphs/brake_current_vs_wattage.png", dpi=200)

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Process Motor Stats')
	parser.add_argument('filename', help='Name of CSV file to parse')
	args = parser.parse_args()

	pd.set_option('display.max_columns', None)
	pd.set_option('display.max_rows', None)
	
	mpl.rcParams['lines.linewidth'] = 1

	df = pd.read_csv(args.filename)

	plot_voltage(df)
	plot_wattage(df)
	plot_brake_current_vs_wattage(df)
	
	#plt.show()

