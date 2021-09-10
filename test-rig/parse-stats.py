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

battery_shunt_data = None
generator_shunt_data = None
loadcell_data = None

def plot_voltage(df, graphs_dir):
	t = df['Time']
	fig, axs = plt.subplots()

	axs.plot(t, df['Driver Voltage'], label="Driver VESC")
	axs.plot(t, df['Gen Voltage'], label="Generator VESC")
	
	if generator_shunt_data is not None:
		axs.plot(generator_shunt_data['Time'], generator_shunt_data['Voltage'], label="Generator Shunt")

	if battery_shunt_data is not None:
		axs.plot(battery_shunt_data['Time'], battery_shunt_data['Voltage'], label="Battery Shunt")
	
	axs.set(title='Voltage', xlabel="Time (s)", ylabel="Voltage")
	axs.legend()
	axs.grid(True)

	#fig.savefig(graphs_dir + "/vesc_voltage.png", dpi=200)

def plot_wattage(df, graphs_dir):
	fig, ax1 = plt.subplots()

	x = df['Time']
	y = df['Driver Wattage']
	ax1.plot(x, y, label="Driver VESC", linewidth=1)
	#plot_cubic(ax1, x, y)

	y = df['Gen Wattage']
	ax1.plot(x, y, label="Generator VESC", linewidth=1)
	#plot_cubic(ax1, x, y)

	if generator_shunt_data is not None:
		ax1.plot(generator_shunt_data['Time'], generator_shunt_data['Wattage'], label="Generator Shunt")

	ax1.set(title='Power Consumed vs. Generated', xlabel="Time (s)", ylabel="Wattage")
	ax1.legend(loc='lower right')
	
	color = 'tab:red'
	ax2 = ax1.twinx()
	
	y = df['Efficiency']
	ax2.plot(x, y, label="Efficiency", color=color)
	#plot_cubic(ax2, x, y)

	ax2.set_ylabel('Efficiency (%)', color=color)
	ax2.tick_params(axis='y', labelcolor=color)
	ax2.legend(loc='lower center')
	
	#fig.savefig(graphs_dir + "/vesc_wattage.png", dpi=200)

def plot_amperage(df, graphs_dir):
	fig, axs = plt.subplots()

	x = df['Time']
	y = df['Driver Amperage']
	axs.plot(x, y, label="Driver VESC", linewidth=1)
	#plot_cubic(axs, x, y)

	y = df['Gen Amperage']
	axs.plot(x, y, label="Generator VESC", linewidth=1)
	#plot_cubic(axs, x, y)

	if generator_shunt_data is not None:
		axs.plot(generator_shunt_data['Time'], generator_shunt_data['Amperage'], label="Generator Shunt")

	if battery_shunt_data is not None:
		axs.plot(battery_shunt_data['Time'], battery_shunt_data['Amperage'], label="Battery Shunt")

	axs.set(title='Amperage', xlabel="Time (s)", ylabel="Amperage")
	axs.legend()
	
	#fig.savefig(graphs_dir + "/vesc_wattage.png", dpi=200)

def plot_rpm_vs_wattage(df, graphs_dir):
	fig, axs = plt.subplots()

	x = df['Gen RPM']
	y = df['Gen Wattage']
	axs.plot(x, y, label="Generator", linewidth=1)

	if generator_shunt_data is not None:
		axs.plot(generator_shunt_data['Time'], generator_shunt_data['Amperage'], label="Generator Shunt")

	if battery_shunt_data is not None:
		axs.plot(battery_shunt_data['Time'], battery_shunt_data['Amperage'], label="Battery Shunt")

	axs.set(title='RPM vs Wattage', xlabel="RPM", ylabel="Wattage")
	axs.legend()
	
	#fig.savefig(graphs_dir + "/vesc_wattage.png", dpi=200)

def plot_brake_current_vs_wattage(df, graphs_dir):
	fig, ax1 = plt.subplots()

	ax1.set(title='Brake Current vs. Wattage', xlabel="Brake Current (A)", ylabel="Wattage (W)")
	ax1.plot(df['Brake Current'], df['Gen Wattage'], label="Generator")

	ax1.legend()
	
	#fig.savefig(graphs_dir + "/brake_current_vs_wattage.png", dpi=200)

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
	parser.set_defaults(show=False)

	parser.add_argument('--voltage', dest='voltage', action='store_true')
	parser.set_defaults(voltage=False)

	parser.add_argument('--amperage', dest='amperage', action='store_true')
	parser.set_defaults(amperage=False)

	parser.add_argument('--wattage', dest='wattage', action='store_true')
	parser.set_defaults(wattage=False)

	parser.add_argument('--rpm_vs_wattage', dest='rpm_vs_wattage', action='store_true')
	parser.set_defaults(rpm_vs_wattage=False)

	parser.add_argument('--brake_current_vs_wattage', dest='brake_current_vs_wattage', action='store_true')
	parser.set_defaults(brake_current_vs_wattage=False)

	args = parser.parse_args()

	pd.set_option('display.max_columns', None)
	pd.set_option('display.max_rows', None)
	
	mpl.rcParams['lines.linewidth'] = 1

	#read our main CSV
	df = pd.read_csv(args.filename)
	df.Time = pd.to_datetime(df.Time, unit='s')
	
	#pprint(df.head())	
	#pprint(df.describe())

	start_time = df.Time.min(0)
	end_time = df.Time.max(0)

	#where to put our graphs
	p = pathlib.Path(args.filename)
	graphs_dir = str(p.parent) + '/graphs'
	pathlib.Path(graphs_dir).mkdir(parents=True, exist_ok=True)

	#generator shunt?
	generator_shunt_filename = str(p.parent) + "/generator-shunt.csv"
	if os.path.isfile(generator_shunt_filename):
		generator_shunt_data = pd.read_csv(generator_shunt_filename)
		generator_shunt_data.Time = pd.to_datetime(generator_shunt_data.Time, unit='s')
		mask = (generator_shunt_data['Time'] >= str(start_time)) & (generator_shunt_data['Time'] <= str(end_time))
		generator_shunt_data = generator_shunt_data.loc[mask]

	#battery shunt?
	battery_shunt_filename = str(p.parent) + "/battery-shunt.csv"
	if os.path.isfile(battery_shunt_filename):
		battery_shunt_data = pd.read_csv(battery_shunt_filename)
		battery_shunt_data.Time = pd.to_datetime(battery_shunt_data.Time, unit='s')
		mask = (battery_shunt_data['Time'] >= str(start_time)) & (battery_shunt_data['Time'] <= str(end_time))
		battery_shunt_data = battery_shunt_data.loc[mask]
		#battery_shunt_data['Amperage'] = battery_shunt_data['Amperage'].apply(lambda x: abs(x))
		

	#load cell?
	loadcell_filename = str(p.parent) + "/loadcell.csv"
	if os.path.isfile(loadcell_filename):
		loadcell_data = pd.read_csv(loadcell_filename)
		loadcell_data.Time = pd.to_datetime(loadcell_data.Time, unit='s')
		mask = (loadcell_data['Time'] >= str(start_time)) & (loadcell_data['Time'] <= str(end_time))
		loadcell_data = loadcell_data.loc[mask]

	if args.voltage:
		plot_voltage(df, graphs_dir)

	if args.amperage:
		plot_amperage(df, graphs_dir)
	
	if args.wattage:
		plot_wattage(df, graphs_dir)

	if args.rpm_vs_wattage:
		plot_rpm_vs_wattage(df, graphs_dir)

	if args.brake_current_vs_wattage:
		plot_brake_current_vs_wattage(df, graphs_dir)
	
	if (args.show):
		plt.show()

