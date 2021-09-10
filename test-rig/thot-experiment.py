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

def test_generator_motor():
	try:
		driver_uuid    = 0x5300450011504d4143323520 # Trampa V60 VESC
		generator_uuid = 0x1b00420012504D4143323520 # Trampa V60 VESC
		#driver_uuid    = 0x400030001850524154373020 # Flipsky FSESC
		#generator_uuid = 0x1c002d000550523947383920 # Flipsky FSESC
		#generator_uuid = 0x580049001550315739383420 # Flipsky 75/300
		
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

		#where so save our csv
		Path("output").mkdir(parents=True, exist_ok=True)

		dir_path = os.path.dirname(os.path.realpath(__file__))
		smartshunt_script = dir_path + "/smartshunt.py"
		
		battery_shunt_params = [smartshunt_script,"--serial", "VE4X8ER8", "--csv", "{}/output/battery-shunt.csv".format(dir_path)]
		#print(" ".join(battery_shunt_params))
		battery_shunt_proc = subprocess.Popen(battery_shunt_params, stdout=subprocess.DEVNULL)
		
		generator_shunt_params = [smartshunt_script,"--serial", "VE4YC71B", "--csv", "{}/output/generator-shunt.csv".format(dir_path)]
		#print(" ".join(generator_shunt_params))
		generator_shunt_proc = subprocess.Popen(generator_shunt_params, stdout=subprocess.DEVNULL)
		
		try:
			min_rpm = 300
			max_rpm = 2500
			
			for rpm in range (min_rpm, max_rpm+1, 100):
				characterise_generator_at_rpm(driver, generator, rpm)
				time.sleep(0.5)

			#for current in range (10, 60+1, 10):
			#	characterise_generator_at_brake_current(driver, generator, current,  start_rpm = min_rpm, end_rpm = max_rpm)
			#	time.sleep(0.5)

			#test_mppt(driver, generator, 5)
			
			#monitor_motor(generator, 60)

		except Exception as e:
			print ("Exception: " + str(e))
			traceback.print_exc()
		
		#characterise_generator_old(driver, generator)
		
	except KeyboardInterrupt:
		True

	# Turn Off the VESC
	driver.set_current(0)
	generator.set_current(0)
	battery_shunt_proc.terminate()
	generator_shunt_proc.terminate()
	driver.stop_heartbeat()
	generator.stop_heartbeat()

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
			
		output =  "[{}] E: {:4.1f}% | RPM: {:4.0f} | BC: {:5.2f}A | "
		output += "Gen: {:4.0f} RPM, {:5.2f}V, {:5.2f}A, {:6.1f}W MOS: {:4.1f}C MOT: {:4.1f}C | "
		output += "Drv: {:4.0f} RPM, {:5.2f}V, {:5.2f}A, {:6.1f}W MOS: {:4.1f}C MOT: {:4.1f}C"
		
		print (output.format(
			time.ctime(), vals['efficiency'], vals['target_rpm'], vals['brake_current'], 
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
				if avg['drv_voltage'] < 26:
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

			thotlog.log('brake_current', test_current)
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
	wait_for_rpm(driver, 1000)
	driver.set_current(drive_current)
	generator.set_brake_current(start_brake_current)
	
	start_time = time.time()
	end_time = start_time + test_duration
	next_display_time = start_time + 0.5
	samples = 0

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

def test_mppt(driver, generator, drive_current, test_duration = None, filename = None):

	if filename is None:
		filename = "output/mppt_{:.0f}A.csv".format(drive_current)
		raw_filename = "output/raw_mppt_{:.0f}A.csv".format(drive_current)
	
	thotlog = ThotLogger(filename, raw_filename)
	
	print ("MPPT Test Current:", drive_current)
	
	#init our test...
	driver.set_rpm(3000)
	wait_for_rpm(driver, 3000)
	driver.set_current(drive_current)
	time.sleep(5)
	generator.set_brake_current(0)
	
	start_time = time.time()
	if test_duration is not None:
		end_time = start_time + test_duration
	next_display_time = start_time + 0.50
	samples = 0

	brake_current = 0
	brake_current = drive_current * 0.3
	last_brake_current = brake_current
	generator.set_brake_current(brake_current)

	last_rpm = 0
	last_wattage = 0
	last_current_change = time.time()
	first_time = True
	
	orig_send_interval = 5
	send_interval = orig_send_interval

	while test_duration is None or time.time() <= end_time:
		try:
			thotlog.new_log()

			thotlog.log_motor(generator, 'gen')
			thotlog.log_motor(driver, 'drv')
			thotlog.log_efficiency()
			thotlog.log('brake_current', brake_current)
			
			#do we want to display it?
			if time.time() > next_display_time:
				avg = thotlog.get_averages()
				thotlog.print_line()
				thotlog.write_avg_csv()

				brake_current = last_brake_current

				percent = 0.005
				big_wattage = last_wattage * (1.0 + percent)
				big_rpm = last_rpm * (1.0 + percent)
				lil_wattage = last_wattage * (1.0 - percent)
				lil_rpm = last_rpm * (1.0 - percent)

				try:
					#print("Watts: {:6.2f} < {:6.2f} < {:6.2f}  RPM: {:4.0f} < {:4.0f} < {:4.0f}".format(lil_wattage, avg['gen_wattage'], big_wattage, lil_rpm, avg['gen_rpm'], big_rpm))

					#wattage up and rpm up - increase
					#if avg['gen_wattage'] >= big_wattage and avg['gen_rpm'] >= big_rpm:
					#	brake_current += 0.1
					#	last_current_change = time.time()
					#	last_rpm = avg['gen_rpm']
					#	last_wattage = avg['gen_wattage']
						#print ("full send")

					#wattage down or rpm down - decrease
					if avg['gen_wattage'] < lil_wattage or avg['gen_rpm'] < lil_rpm:
						brake_current -= 0.02
						last_current_change = time.time()
						last_rpm = avg['gen_rpm']
						last_wattage = avg['gen_wattage']
						#print ("chill bro")
						send_interval = orig_send_interval

					#has it been too long since we tried to increase				
					if time.time() - last_current_change > send_interval:
						brake_current += 0.01
						last_current_change = time.time()
						last_rpm = avg['gen_rpm']
						last_wattage = avg['gen_wattage']
						#print ("lets get it")
						send_interval = send_interval - 1
						send_interval = max(1, send_interval)
						
						
					generator.set_brake_current(brake_current)
					last_brake_current = brake_current

					thotlog.clear_averages()

					next_display_time = time.time() + 1
					
					#if we hit the end of the power curve, exit
					if avg['gen_wattage'] < 0 and time.time() - start_time > test_duration/2:
						print ("End of power curve.")					
						break

					#if we pull the battery too low, exit
					if avg['drv_voltage'] < 24:
						print ("Battery voltage too low")
						break;


					samples += 1

				except TypeError as e:
					print ("yarr.")
			#okay, write it to our csv...
		except AttributeError as e:
			print (e)
			traceback.print_exc()
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
