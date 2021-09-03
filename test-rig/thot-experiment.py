#!/usr/bin/python3
# -*- coding: utf-8 -*-

from pyvesc import VESC
from pyvesc.VESC.messages import *

import time
from datetime import datetime
import statistics
from construct import *
from pprint import pprint
from vedirect import Vedirect
import os
import csv
import traceback
from pathlib import Path

class ThotLogger():

	names = {
		'efficiency': 'Efficiency',
		'target_rpm': 'Target RPM',
		'brake_current': 'Brake Current',
		'gen_rpm': 'Gen RPM',
		'gen_voltage': 'Gen Voltage',
		'gen_amperage': 'Gen Amperage',
		'gen_wattage': 'Gen Wattage',
		'gen_fet_temp': 'Gen FET Temp',
		'gen_motor_temp': 'Gen Motor Temp',
		'drv_rpm': 'Driver RPM',
		'drv_voltage': 'Driver Voltage',
		'drv_amperage': 'Driver Amperage',
		'drv_wattage': 'Driver Wattage',
		'drv_fet_temp': 'Driver FET Temp',
		'drv_motor_temp': 'Driver Motor Temp'
	}

	def __init__(self, csv_filename, raw_filename):
		self.new_log()
		self.clear_averages()

		self.csv_file = open(csv_filename, "w", newline='')
		self.csv_writer = csv.writer(self.csv_file)
		
		header = ['Time']
		header += self.names.values()
		self.csv_writer.writerow(header)

		self.raw_file = open(raw_filename, "w", newline='')
		self.raw_writer = csv.writer(self.raw_file)
		self.raw_writer.writerow(header)

	def log_motor(self, motor, mt = 'gen'):
		measurements = motor.get_measurements()
		rpm = abs(measurements.rpm / (motor.conf.motor_poles / 2))
		voltage = measurements.v_in
		amperage = measurements.avg_input_current
		
		#make it easier for later.
		if mt == 'gen':
			amperage = -amperage
		
		wattage = voltage * amperage
		temp_fet = measurements.temp_fet
		temp_motor = measurements.temp_motor

		if temp_motor >= 150:
			temp_motor = 0.0

		fault_code = int(measurements.mc_fault_code)
		if fault_code != 0:
			raise Exception("Generator fault code: " + VESC.fault_codes[fault_code])

		self.log(mt + '_rpm', rpm)
		self.log(mt + '_voltage', voltage)
		self.log(mt + '_amperage', amperage)
		self.log(mt + '_wattage', wattage)
		self.log(mt + '_fet_temp', temp_fet)
		self.log(mt + '_motor_temp', temp_motor)

	def log_efficiency(self):
		drv_wattage = self.lastlog['drv_wattage']
		gen_wattage = self.lastlog['gen_wattage']
		if (drv_wattage != 0):
			efficiency = 100 * (gen_wattage / drv_wattage)
		else:
			efficiency = 0
		self.log('efficiency', efficiency)

	def log(self, name, value):
		self.lastlog[name] = value;
		if name not in self.averages:
			self.averages[name] = []
		self.averages[name].append(value)
		return
		
	def get_averages(self):
		rvals = {}
		for key, avg_array in self.averages.items():
			if avg_array:
				avg = statistics.mean(avg_array)
			else:
				#todo: make this support being None
				avg = 0
			rvals[key] = avg

		return rvals

	def write_raw_csv(self):
		date_string = time.time()
		#date_string = datetime.now().isoformat()
		row = [date_string]
		row += self.lastlog.values()
		self.raw_writer.writerow(row)
	
	def write_avg_csv(self):
		date_string = time.time()
		#date_string = datetime.now().isoformat()
		row = [date_string]
		row += self.get_averages().values()
		self.csv_writer.writerow(row)

	def print_line(self, vals = None):

		if vals is None:
			vals = self.get_averages()
			
		output =  "{:13.2f} | E: {:4.1f}% | RPM: {:4.0f} | BC: {:5.2f}A | "
		output += "Gen: {:4.0f} RPM, {:4.1f}V, {:5.2f}A, {:6.1f}W MOS: {:4.1f}C MOT: {:4.1f}C | "
		output += "Drv: {:4.0f} RPM, {:4.1f}V, {:5.2f}A, {:6.1f}W MOS: {:4.1f}C MOT: {:4.1f}C"
		
		print (output.format(
			time.time(), vals['efficiency'], vals['target_rpm'], vals['brake_current'], 
			vals['gen_rpm'], vals['gen_voltage'], vals['gen_amperage'], vals['gen_wattage'], vals['gen_fet_temp'], vals['gen_motor_temp'],
			vals['drv_rpm'], vals['drv_voltage'], vals['drv_amperage'], vals['drv_wattage'], vals['drv_fet_temp'], vals['drv_motor_temp']
		))
	

	def new_log(self):
		self.lastlog = {}
		for key in self.names.keys():
			self.lastlog[key] = None
		
	def clear_averages(self):
		self.averages = {}
		for key in self.names.keys():
			self.averages[key] = []

# a function to show how to use the class with a with-statement
def test_generator_motor():
	try:
		driver_uuid = 0x400030001850524154373020
		generator_uuid = 0x1c002d000550523947383920
		#generator_uuid = 0x580049001550315739383420
		
		driver_port = VESC.get_vesc_serial_port_by_uuid(driver_uuid)
		generator_port = VESC.get_vesc_serial_port_by_uuid(generator_uuid)
		
		if driver_port:
			driver = VESC(serial_port = driver_port)
			print("Driver Firmware: ", driver.get_firmware_version(), " / UUID: ", hex(driver.uuid))
		else:
			print("Could not find driver.")
			return

		#pprint(vars(driver.conf))
		#pprint(vars(driver.get_measurements()))

		if generator_port:
			generator = VESC(serial_port = generator_port)
			print("Generator Firmware: ", generator.get_firmware_version(), " / UUID: ", hex(generator.uuid))
		else:
			print("Could not find generator.")
			return

		#pprint(vars(generator.conf))
		#pprint(vars(generator.get_measurements()))

		dir_path = os.path.dirname(os.path.realpath(__file__))

		driver_port = '/dev/ttyUSB0'
		#driver_pid = os.spawnlp(os.P_NOWAIT, dir_path + "/smartshunt.py", "port", driver_port)

		generator_port = '/dev/ttyUSB1'

		#where so save our csv
		Path("output").mkdir(parents=True, exist_ok=True)

		try:
			max_rpm = 2500
			
			#for rpm in range (1000, max_rpm+1, 100):
			#	characterise_generator_at_rpm(driver, generator, rpm)
			#	time.sleep(0.5)
			#characterise_generator_at_rpm(driver, generator, 1000)

			#for current in range (10, 60+1, 10):
			#	characterise_generator_at_brake_current(driver, generator, current, end_rpm = max_rpm)
			#	time.sleep(0.5)
			#characterise_generator_at_brake_current(driver, generator, 10, start_rpm = 300, end_rpm = max_rpm)

			characterise_generator_at_drive_current(driver, generator, 10, 0, 20)

		except Exception as e:
			print ("Exception: " + str(e))
			traceback.print_exc()
		
		#characterise_generator_old(driver, generator)
		
	except KeyboardInterrupt:
		# Turn Off the VESC
		driver.set_current(0)
		generator.set_current(0)

	#os.kill(driver_pid)
	#os.kill(driver_pid)
	
	driver.stop_heartbeat()
	generator.stop_heartbeat()




def characterise_generator_at_rpm(driver, generator, test_rpm, start_current = 0, end_current = 60, test_duration = 30, filename = None):

	if filename is None:
		filename = "output/generator_rpm_{:.0f}_{:.0f}A_to_{:.0f}A_{:.0f}s.csv".format(test_rpm, start_current, end_current, test_duration)
		raw_filename = "output/raw_generator_rpm_{:.0f}_{:.0f}A_to_{:.0f}A_{:.0f}s.csv".format(test_rpm, start_current, end_current, test_duration)
	
	thotlog = ThotLogger(filename, raw_filename)

	print ("Test RPM:", test_rpm)
	driver.set_rpm(test_rpm)
	wait_for_rpm(driver, test_rpm)

	start_time = time.time()
	next_display_time = start_time + 0.25
	end_time = start_time + test_duration
	samples = 0

	while time.time() <= end_time:
		#set our brake current to be proportional based on time
		current_range = end_current - start_current
		brake_current = start_current + current_range - current_range * ((end_time - time.time()) / test_duration)
		generator.set_brake_current(brake_current)

		try:
			thotlog.new_log()

			thotlog.log('brake_current', brake_current)
			thotlog.log_motor(generator, 'gen')
			thotlog.log_motor(driver, 'drv')
			thotlog.log_efficiency()
			
			thotlog.write_raw_csv()

			#do we want to display it?
			if time.time() > next_display_time:
				avg = thotlog.get_averages()
				thotlog.print_line()
				thotlog.write_avg_csv()
				thotlog.clear_averages()

				next_display_time = time.time() + 0.25
				
				#if we hit the end of the power curve, exit
				if avg['gen_wattage'] < 0 and time.time() - start_time > test_duration/2:
					print ("End of power curve.")					
					break

				#if we pull the battery too low, exit
				if avg['drv_voltage'] < 24:
					print ("Battery voltage too low")
					break;
				
			samples += 1

		except AttributeError as e:
			print (e)
			continue

	driver.set_rpm(0)
	generator.set_brake_current(0)

	print ("Finished test with {} samples.".format(samples))


def characterise_generator_at_brake_current(driver, generator, test_current, start_rpm = 500, end_rpm = 3000, test_duration = 60, filename = None):

	if filename is None:
		filename = "output/generator_current_{:.0f}_{:.0f}RPM_to_{:.0f}RPM_{:.0f}s.csv".format(test_current, start_rpm, end_rpm, test_duration)
		raw_filename = "output/raw_generator_current_{:.0f}_{:.0f}RPM_to_{:.0f}RPM_{:.0f}s.csv".format(test_current, start_rpm, end_rpm, test_duration)
	
	thotlog = ThotLogger(filename, raw_filename)
	
	print ("Test Current:", test_current)
	
	#init our test...
	driver.set_rpm(start_rpm)
	wait_for_rpm(driver, start_rpm)
	generator.set_brake_current(test_current)
	wait_for_rpm(driver, start_rpm)
	
	start_time = time.time()
	end_time = start_time + test_duration
	next_display_time = start_time + 0.5
	samples = 0
	
	while time.time() <= end_time:
		#set our brake current to be proportional based on time
		rpm_range = end_rpm - start_rpm
		test_rpm = start_rpm + rpm_range - rpm_range * ((end_time - time.time()) / test_duration)

		driver.set_rpm(int(test_rpm))

		try:
			thotlog.new_log()

			thotlog.log('target_rpm', test_rpm)
			thotlog.log_motor(generator, 'gen')
			thotlog.log_motor(driver, 'drv')
			thotlog.log_efficiency()
			
			thotlog.write_raw_csv()

			#do we want to display it?
			if time.time() > next_display_time:
				avg = thotlog.get_averages()
				thotlog.print_line()
				thotlog.write_avg_csv()
				thotlog.clear_averages()

				next_display_time = time.time() + 0.25
				
				#if we hit the end of the power curve, exit
				if avg['gen_wattage'] < 0 and time.time() - start_time > test_duration/2:
					print ("End of power curve.")					
					break

				#if we pull the battery too low, exit
				if avg['drv_voltage'] < 24:
					print ("Battery voltage too low")
					break;

			samples += 1

			#okay, write it to our csv...
		except AttributeError as e:
			print (e)
			continue
					
	#turn it off
	driver.set_rpm(0)
	generator.set_brake_current(0)

	print ("Finished test with {} samples.".format(samples))

def characterise_generator_at_drive_current(driver, generator, drive_current, start_brake_current = 0, end_brake_current = 60, test_duration = 60, filename = None):

	if filename is None:
		filename = "output/generator_drive_current_{:.0f}_{:.0f}A_to_{:.0f}A_{:.0f}s.csv".format(drive_current, start_brake_current, end_brake_current, test_duration)
		raw_filename = "output/raw_generator_drive_current_{:.0f}_{:.0f}A_to_{:.0f}A_{:.0f}s.csv".format(drive_current, start_brake_current, end_brake_current, test_duration)
	
	thotlog = ThotLogger(filename, raw_filename)
	
	print ("Test Drive Current:", drive_current)
	
	#init our test...
	driver.set_rpm(1000)
	print ("Here1")
	wait_for_rpm(driver, 1000)
	print ("Here2")
	driver.set_current(drive_current)
	print ("Here3")
	generator.set_brake_current(start_brake_current)
	print ("Here4")

	print ("Here5")
	
	start_time = time.time()
	end_time = start_time + test_duration
	next_display_time = start_time + 0.5
	samples = 0

	print ("Here2")
	
	while time.time() <= end_time:
		#set our brake current to be proportional based on time
		brake_current_range = end_brake_current - start_brake_current
		brake_current = start_brake_current + brake_current_range - brake_current_range * ((end_time - time.time()) / test_duration)

		generator.set_brake_current(brake_current)

		try:
			thotlog.new_log()

			thotlog.log('brake_current', brake_current)
			thotlog.log_motor(generator, 'gen')
			thotlog.log_motor(driver, 'drv')
			thotlog.log_efficiency()
			
			thotlog.write_raw_csv()

			#do we want to display it?
			if time.time() > next_display_time:
				avg = thotlog.get_averages()
				thotlog.print_line()
				thotlog.write_avg_csv()
				thotlog.clear_averages()

				next_display_time = time.time() + 0.25
				
				#if we hit the end of the power curve, exit
				if avg['gen_wattage'] < 0 and time.time() - start_time > test_duration/2:
					print ("End of power curve.")					
					break

				#if we pull the battery too low, exit
				if avg['drv_voltage'] < 24:
					print ("Battery voltage too low")
					break;

			samples += 1

			#okay, write it to our csv...
		except AttributeError as e:
			print (e)
			continue
					
	#turn it off
	driver.set_rpm(0)
	generator.set_brake_current(0)

	print ("Finished test with {} samples.".format(samples))

def wait_for_rpm(motor, target_rpm):
	start_time = time.time()
	current_rpm = 0
	ratio = 0
	while ratio < .99 or ratio > 1.01:
		current_rpm = motor.get_rpm()
		ratio = current_rpm / target_rpm

		time.sleep(0.1)

		if (time.time() > start_time + 30):
			print ("Error: timeout exceeded")
			break
	
def duty_cycle_ramp(motor):
	print ("Duty Cycle Ramp Up")
	for i in range (1, 100):
		motor.set_duty_cycle(i/100)
		time.sleep(0.1)
	print ("Duty Cycle Ramp Down")
	for i in range (1, 100):
		motor.set_duty_cycle((100-i)/100)
		time.sleep(0.1)
	motor.set_duty_cycle(0)

def current_ramp(motor):
	print ("Current Ramp Up")
	for i in range (1, 10):
		motor.set_current(i)
		time.sleep(1)
	print ("Amperage Ramp Down")
	for i in range (1, 10):
		motor.set_current(10-i)
		time.sleep(1)
	motor.set_current(0)

def rpm_ramp(motor):
	print ("RPM Ramp Up")
	for i in range (100, 1800, 100):
		motor.set_rpm(i)
		time.sleep(1)
	print ("RPM Ramp Down")
	for i in range (100, 1800, 100):
		motor.set_rpm(1800-i)
		time.sleep(1)
	motor.set_rpm(0)

def servo_test(motor):
	print ("Servo Test Up")
	for i in range (1, 100):
		motor.set_servo(i/100)
		time.sleep(0.1)
	print ("Servo Test Down")
	for i in range (1, 100):
		motor.set_servo((100-i)/100)
		time.sleep(0.1)
	motor.set_duty_cycle(0)

if __name__ == '__main__':
	test_generator_motor()
	
#print ("Driver Measurements:");
#pprint(vars(driver.get_measurements()))

#test what frequency of updates we can get....
#driver.set_duty_cycle(0.2)
#count = 0
#start = time.time()
#for i in range(1, 10000):
#	data = driver.get_measurements()
#	count += 1
#end = time.time()
#total = end - start
#print(10000 / total, " updates / sec")

#print ("Generator Measurements:");
#pprint(vars(generator.get_measurements()))

#duty_cycle_ramp(driver)
#current_ramp(driver)
#rpm_ramp(driver)
#servo_test(driver)

#pprint(driver.get_rpm())
#pprint(driver.get_duty_cycle())
#pprint(driver.get_v_in())
#pprint(driver.get_motor_current())
#pprint(driver.get_incoming_current())

# run motor and print out rpm for ~2 seconds
#for i in range(30):
#	time.sleep(0.1)
#	print("RPM:", motor.get_measurements().rpm)
#motor.set_rpm(0)
