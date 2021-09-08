#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse, os
import time
import csv
import serial
import serial.tools.list_ports
from pprint import pprint
import re

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Read data from loadcell Arduino script')
	parser.add_argument('--port', help='Serial port', default=None)
	parser.add_argument('--timeout', help='Serial port read timeout', type=int, default='60')
	parser.add_argument('--serial', help='Serial # of serial port', default=None)

	parser.add_argument('--csv', help='CSV file to output to', type=str, default=None)

	parser.add_argument('--list', dest='list', action='store_true')
	parser.set_defaults(list=False)

	args = parser.parse_args()

	if args.list:
		print ("Port\t\tVID:PID\t\tSerial")
		ports = serial.tools.list_ports.comports()
		for port in ports:
			print("{}\t{:04x}:{:04x}\t{}".format(port.device, port.vid, port.pid, port.serial_number))
	else:
		if args.serial:
			ports = serial.tools.list_ports.comports()
			for port in ports:
				if port.serial_number == args.serial:
					args.port = port.device
					print ("Found {}".format(args.port))

		try: 
			print ("Opening {}".format(args.port))
			ser = serial.Serial(port=args.port, baudrate=9600)
			time.sleep(1)
		except Exception as e:
			print ("Error opening serial port: " + str(e))
			exit()	
		
		csv_writer = None
		if args.csv:
			csv_file = open(args.csv, "w", newline='')
			csv_writer = csv.writer(csv_file)
			csv_writer.writerow(("Timestamp", "Human Time", "Weight"))

		if ser.isOpen():
			ser.flushInput()
			ser.flushOutput()
			try:
				while True:
					if ser.inWaiting() > 0:
						line = ser.readline().decode('ascii')
						line = line.strip()
						data = line.split(',')

						try:
							weight = float(data[0])
							print("[{}] {:6.3f}KG".format(time.ctime(), weight))
							
							if csv_writer:
								csv_writer.writerow((time.time(), time.ctime(), weight))

						except ValueError:
							continue
					else:
						time.sleep(0.01)
			except KeyboardInterrupt:
				csv_file.close()
				ser.close()
		else:
			print ("Exiting.")		
