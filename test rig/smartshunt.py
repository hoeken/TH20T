#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse, os
from vedirect import Vedirect
import time

def print_data_callback(packet):
	try:
		#pprint(packet)
		voltage = int(packet.get('V', 0)) / 1000.0
		amperage = int(packet.get('I', 0)) / 1000.0
		wattage = packet.get('P', 0)

		print("{},{:.3f},{:.3f},{}".format(time.time(), voltage, amperage, wattage))
	except AttributeError as e:
		print (e)

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Process VE.Direct protocol')
	parser.add_argument('--port', help='Serial port')
	parser.add_argument('--timeout', help='Serial port read timeout', type=int, default='60')
	args = parser.parse_args()

	print ("Time,Voltage,Amperage,Wattage")
	ve = Vedirect(args.port, args.timeout)

	try:
		ve.read_data_callback(print_data_callback)
	except KeyboardInterrupt:
		True

