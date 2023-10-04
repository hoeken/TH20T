#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse, os
import vedirect
import time
import os
import csv
import serial
import serial.tools.list_ports
import signal
from pprint import pprint

class GracefulKiller:
	kill_now = False
	def __init__(self):
		signal.signal(signal.SIGINT, self.exit_gracefully)
		signal.signal(signal.SIGTERM, self.exit_gracefully)

	def exit_gracefully(self, *args):
		self.kill_now = True
		csv_file.close()

csv_file = None
csv_writer = None

def print_data_callback(packet):
	try:
		#pprint(packet)
		voltage = int(packet.get('V', 0)) / 1000.0
		amperage = int(packet.get('I', 0)) / 1000.0
		wattage = packet.get('P', 0)

		print("[{}] {:.3f}V {:.3f}A {}W".format(time.ctime(), voltage, amperage, wattage))
		
		if csv_file:
			csv_writer.writerow((time.time(), voltage, amperage, wattage))
			csv_file.flush()

	except AttributeError as e:
		print (e)

if __name__ == '__main__':
	killer = GracefulKiller()

	parser = argparse.ArgumentParser(description='Process VE.Direct protocol')

	parser.add_argument('--list', dest='list', action='store_true')
	parser.set_defaults(list=False)
	parser.add_argument('--port', help='Serial port')
	parser.add_argument('--serial', help='Serial # of serial port', default=None)
	parser.add_argument('--timeout', help='Serial port read timeout', type=int, default='60')
	parser.add_argument('--csv', help='CSV file to output to', type=str, default=None)

	args = parser.parse_args()

	if args.list:
		print ("Port\t\tVID:PID\t\tSerial")
		ports = serial.tools.list_ports.comports()
		for port in ports:
			print(f"{port.device}\t{port.serial_number}")
	else:
		if args.serial:
			ports = serial.tools.list_ports.comports()
			for port in ports:
				pprint(port.serial_number)
				if port.serial_number == args.serial:
					args.port = port.device
					print ("Found {}".format(args.port))

		ve = vedirect.Vedirect(args.port, args.timeout)
		
		if args.csv:
			csv_file = open(args.csv, "w", newline='')
			csv_writer = csv.writer(csv_file)
			csv_writer.writerow(("Time", "Voltage", "Amperage", "Wattage"))

		try:
			ve.read_data_callback(print_data_callback)
		except ValueError:
			True
	
		csv_file.close()
