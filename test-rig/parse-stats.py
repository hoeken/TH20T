#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse, os
import time
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
#import seaborn as sns
import numpy as np
from scipy.interpolate import interp1d
from scipy.interpolate import make_interp_spline
import pathlib

from pprint import pprint

def plot_voltage(df, graphs_dir):
	t = df['Time']
	fig, axs = plt.subplots()

	axs.plot(t, df['Driver Voltage'], label="Driver")
	axs.plot(t, df['Gen Voltage'], label="Generator")
	axs.set(title='Voltage', xlabel="Time", ylabel="Voltage")
	axs.legend()
	axs.grid(True)

	fig.savefig(graphs_dir + "/vesc_voltage.png", dpi=200)

def plot_wattage(df, graphs_dir):
	fig, ax1 = plt.subplots()

	x = df['Time']
	y = df['Driver Wattage']
	ax1.plot(x, y, label="Driver", linewidth=1)
	#plot_cubic(ax1, x, y)

	y = df['Gen Wattage']
	ax1.plot(x, y, label="Generator", linewidth=1)
	#plot_cubic(ax1, x, y)

	ax1.set(title='Power Consumed vs. Generated', xlabel="Time", ylabel="Wattage")
	ax1.legend(loc='lower right')
	
	color = 'tab:red'
	ax2 = ax1.twinx()
	
	y = df['Efficiency']
	ax2.plot(x, y, label="Efficiency", color=color)
	#plot_cubic(ax2, x, y)

	ax2.set_ylabel('Efficiency (%)', color=color)
	ax2.tick_params(axis='y', labelcolor=color)
	ax2.set(title='Power Consumed vs. Generated', xlabel="Time", ylabel="Wattage")
	ax2.legend(loc='lower center')
	
	fig.savefig(graphs_dir + "/vesc_wattage.png", dpi=200)

def plot_brake_current_vs_wattage(df, graphs_dir):
	t = df['Time']
	fig, ax1 = plt.subplots()

	ax1.set(title='Brake Current vs. Wattage', xlabel="Time", ylabel="Wattage")
	ax1.plot(t, df['Gen Wattage'], label="Generator Wattage")
	
	color = 'tab:red'
	ax2 = ax1.twinx()
	ax2.plot(t, df['Brake Current'], label="Brake Current", color=color)
	ax2.set_ylabel('Brake Current', color=color)
	ax2.tick_params(axis='y', labelcolor=color)
	
	fig.savefig(graphs_dir + "/brake_current_vs_wattage.png", dpi=200)

def plot_spline(ax, x, y):
	# Plotting the graph - spline
	X_Y_Spline = make_interp_spline(x, y)
	X_ = np.linspace(x.min(), x.max(), 25)
	Y_ = X_Y_Spline(X_)

	X_Y_Spline = make_interp_spline(X_, Y_)
	X2_ = np.linspace(x.min(), x.max(), 500)
	Y2_ = X_Y_Spline(X2_)

	#ax.plot(X_, Y_)
	ax.plot(X2_, Y2_)

def plot_cubic(ax, x, y):
	# Plotting the Graph - cubic
	cubic_interploation_model = interp1d(x, y, kind = "cubic")
	X_=np.linspace(x.min(), x.max(), 25)
	Y_=cubic_interploation_model(X_)

	cubic_interploation_model = interp1d(X_, Y_, kind = "cubic")
	X2_=np.linspace(X_.min(), X_.max(), 500)
	Y2_=cubic_interploation_model(X2_)

	#ax.plot(X_, Y_)
	ax.plot(X2_, Y2_)

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Process Motor Stats')
	parser.add_argument('filename', help='Name of CSV file to parse')

	parser.add_argument('--show', dest='show', action='store_true')
	parser.add_argument('--no-show', dest='show', action='store_false')
	parser.set_defaults(show=False)


	args = parser.parse_args()

	pd.set_option('display.max_columns', None)
	pd.set_option('display.max_rows', None)
	
	mpl.rcParams['lines.linewidth'] = 1

	df = pd.read_csv(args.filename)

	#where so save our csv
	p = pathlib.Path(args.filename)
	graphs_dir = str(p.parent) + '/graphs'
	pathlib.Path(graphs_dir).mkdir(parents=True, exist_ok=True)


	plot_voltage(df, graphs_dir)
	plot_wattage(df, graphs_dir)
	plot_brake_current_vs_wattage(df, graphs_dir)
	
	if (args.show):
		plt.show()

