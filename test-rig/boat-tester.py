#!/usr/bin/python3
# -*- coding: utf-8 -*-

from pyvesc import VESC
import time
import statistics
from pprint import pprint
import os
import csv
import traceback
from pathlib import Path
import subprocess
import serial
import serial.tools.list_ports

def test_generator_motor():
	try:
		generator_uuid = 0x1b00420012504D4143323520 # Trampa V60 VESC
		#driver_uuid    = 0x400030001850524154373020 # Flipsky FSESC
		#generator_uuid = 0x1c002d000550523947383920 # Flipsky FSESC
		#generator_uuid = 0x580049001550315739383420 # Flipsky 75/300
		
		generator_port = VESC.get_vesc_serial_port_by_uuid(generator_uuid)
		
		if generator_port:
			generator = VESC(serial_port = generator_port)
			print("Generator Firmware: ", generator.get_firmware_version())
		else:
			print("Could not find generator.")
			return

		#pprint(vars(generator.conf))
		#pprint(vars(generator.get_measurements()))

		#where so save our csv
		Path("output").mkdir(parents=True, exist_ok=True)

		dir_path = os.path.dirname(os.path.realpath(__file__))
		smartshunt_script = dir_path + "/smartshunt.py"
		
		battery_shunt_params = [smartshunt_script,"--serial", "VE4YC71B", "--csv", "{}/output/battery-shunt.csv".format(dir_path)]
		print(" ".join(battery_shunt_params))
		battery_shunt_proc = subprocess.Popen(battery_shunt_params, stdout=subprocess.DEVNULL)
		
		generator_shunt_params = [smartshunt_script,"--serial", "VE4X8ER8", "--csv", "{}/output/generator-shunt.csv".format(dir_path)]
		print(" ".join(generator_shunt_params))
		generator_shunt_proc = subprocess.Popen(generator_shunt_params, stdout=subprocess.DEVNULL)
		
		try:
			test_duration = 30
			
			for current in range (1, 10, 1):
				characterise_generator_at_brake_current(generator, current, test_duration = test_duration)
				time.sleep(0.5)

			for current in range (10, 60+1, 5):
				characterise_generator_at_brake_current(generator, current, test_duration = test_duration)
				time.sleep(0.5)

			test_mppt(driver, generator, 5)
			
			#monitor_motor(generator, 60)

		except Exception as e:
			print ("Exception: " + str(e))
			traceback.print_exc()
		
	except KeyboardInterrupt:
		True

	# Turn Off the VESC
	generator.set_current(0)
	battery_shunt_proc.terminate()
	generator_shunt_proc.terminate()
	generator.stop_heartbeat()

class ThotLogger():

	names = {
		'brake_current': 'Brake Current',
		'gen_rpm': 'Gen RPM',
		'gen_voltage': 'Gen Voltage',
		'gen_amperage': 'Gen Amperage',
		'gen_wattage': 'Gen Wattage',
		'gen_fet_temp': 'Gen FET Temp',
		'gen_motor_temp': 'Gen Motor Temp',
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
		row = [date_string]
		row += self.lastlog.values()
		self.raw_writer.writerow(row)
	
	def write_avg_csv(self):
		date_string = time.time()
		row = [date_string]
		row += self.get_averages().values()
		self.csv_writer.writerow(row)

	def print_line(self, vals = None):

		if vals is None:
			vals = self.get_averages()
			
		output =  "[{}] BC: {:5.2f}A | "
		output += "Gen: {:4.0f} RPM, {:5.2f}V, {:5.2f}A, {:6.1f}W MOS: {:4.1f}C MOT: {:4.1f}C "
		
		print (output.format(
			time.ctime(), vals['brake_current'], 
			vals['gen_rpm'], vals['gen_voltage'], vals['gen_amperage'], vals['gen_wattage'], vals['gen_fet_temp'], vals['gen_motor_temp']
		))
	

	def new_log(self):
		self.lastlog = {}
		for key in self.names.keys():
			self.lastlog[key] = None
		
	def clear_averages(self):
		self.averages = {}
		for key in self.names.keys():
			self.averages[key] = []

def wait_for_motor_temp(motor, temperature = 46):

	measurements = motor.get_measurements()
	temp_fet = measurements.temp_fet
	temp_motor = measurements.temp_motor

	if temp_motor >= 150:
		temp_motor = 0.0

	while temp_fet > temperature or temp_motor > temperature:
		print ("Waiting for cooldown MOS: {:4.1f}C MOT: {:4.1f}C".format(temp_fet, temp_motor))
		time.sleep(1)
		measurements = motor.get_measurements()
		temp_fet = measurements.temp_fet
		temp_motor = measurements.temp_motor
		if temp_motor >= 150:
			temp_motor = 0.0

def monitor_motor(motor, test_duration = None, filename = None):

	if filename is None:
		filename = "output/monitor.csv"
		raw_filename = "output/raw_monitor.csv"
	
	thotlog = ThotLogger(filename, raw_filename)
	
	start_time = time.time()
	if test_duration is not None:
		end_time = start_time + test_duration
	next_display_time = start_time + 1
	samples = 0

	while test_duration is None or time.time() <= end_time:
		try:
			thotlog.new_log()
			thotlog.log_motor(motor, 'gen')
			thotlog.write_raw_csv()
						
			#do we want to display it?
			if time.time() > next_display_time:
				avg = thotlog.get_averages()
				thotlog.print_line()
				thotlog.write_avg_csv()
				thotlog.clear_averages()

				next_display_time = time.time() + 1
					
				samples += 1
		except AttributeError as e:
			print (e)
			traceback.print_exc()
			continue

	print ("Finished test with {} samples.".format(samples))
	
def characterise_generator_at_brake_current(generator, test_current, test_duration = 60, filename = None):

	#wait_for_motor_temp(generator)

	if filename is None:
		filename = "output/generator_current_{:.0f}_{:.0f}s.csv".format(test_current, test_duration)
		raw_filename = "output/raw_generator_current_{:.0f}__{:.0f}s.csv".format(test_current, test_duration)
	
	thotlog = ThotLogger(filename, raw_filename)
	
	print ("Test Current:", test_current)
	
	#init our test...
	generator.set_brake_current(test_current)
	
	start_time = time.time()
	end_time = start_time + test_duration
	next_display_time = start_time + 0.5
	samples = 0
	
	while time.time() <= end_time:
		try:
			thotlog.new_log()

			thotlog.log('brake_current', test_current)
			thotlog.log_motor(generator, 'gen')
			
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

			samples += 1

			#okay, write it to our csv...
		except AttributeError as e:
			print (e)
			continue
					
	#turn it off
	generator.set_brake_current(0)

	print ("Finished test with {} samples.".format(samples))

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
