from pyvesc import VESC
from pyvesc.VESC.messages import *

import time
import statistics
from construct import *
from pprint import pprint

# a function to show how to use the class with a with-statement
def test_generator_motor():

	driver_uuid = 0x400030001850524154373020
	generator_uuid = 0x1c002d000550523947383920

	driver_port = VESC.get_vesc_serial_port_by_uuid(driver_uuid)
	generator_port = VESC.get_vesc_serial_port_by_uuid(generator_uuid)
    
	if driver_port:
		driver = VESC(serial_port = driver_port)
		print("Driver Firmware: ", driver.get_firmware_version(), " / UUID: ", hex(driver.uuid))
	else:
		print("Could not find driver.")
		return

	if generator_port:
		generator = VESC(serial_port = generator_port)
		print("Generator Firmware: ", generator.get_firmware_version(), " / UUID: ", hex(generator.uuid))
	else:
		print("Could not find generator.")
		return

	try:	
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

		#for rpm in range (1000, 13000, 1000):
		#	characterise_generator_at_rpm(driver, generator, rpm)
	
		for current in range (0, 60, 5):
			characterise_generator_at_brake_current(driver, generator, current)
		
	except KeyboardInterrupt:
		# Turn Off the VESC
		driver.set_current(0)
		generator.set_current(0)

	driver.stop_heartbeat()
	generator.stop_heartbeat()


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
	for i in range (1000, 10000, 250):
		motor.set_rpm(i)
		time.sleep(1)
	print ("RPM Ramp Down")
	for i in range (1000, 10000, 250):
		motor.set_rpm(10000-i)
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

def characterise_generator_at_rpm(driver, generator, test_rpm, start_current = 0, end_current = 60, test_duration = 60):
	print ("Test RPM:", test_rpm)
	driver.set_rpm(test_rpm)
	wait_for_rpm(driver, test_rpm)

	start_time = time.time()
	end_time = start_time + test_duration
	next_display_time = 0
	samples = 0

	avg_brake_current_array = []
	avg_gen_rpm_array = []
	avg_gen_voltage_array = []
	avg_gen_amperage_array = []
	avg_gen_wattage_array = []
	avg_drv_rpm_array = []
	avg_drv_voltage_array = []
	avg_drv_amperage_array = []
	avg_drv_wattage_array = []
	
	while time.time() <= end_time:
		#set our brake current to be proportional based on time
		current_range = end_current - start_current
		brake_current = start_current + current_range - current_range * ((end_time - time.time()) / test_duration)
		generator.set_brake_current(brake_current)

		try:
			measurements = generator.get_measurements()
			gen_rpm = measurements.rpm
			gen_voltage = measurements.v_in
			gen_amperage = -measurements.avg_input_current
			gen_wattage = gen_voltage * gen_amperage

			measurements = driver.get_measurements()
			drv_rpm = measurements.rpm
			drv_voltage = measurements.v_in
			drv_amperage = measurements.avg_input_current
			drv_wattage = drv_voltage * drv_amperage

			avg_brake_current_array.append(brake_current)
			avg_gen_rpm_array.append(gen_rpm)
			avg_gen_voltage_array.append(gen_voltage)
			avg_gen_amperage_array.append(gen_amperage)
			avg_gen_wattage_array.append(gen_wattage)
			avg_drv_rpm_array.append(drv_rpm)
			avg_drv_voltage_array.append(drv_voltage)
			avg_drv_amperage_array.append(drv_amperage)
			avg_drv_wattage_array.append(drv_wattage)

			
			if (drv_wattage != 0):
				efficiency = 100 * (gen_wattage / drv_wattage)
			else:
				efficiency = 0

			#do we want to display it?
			if time.time() > next_display_time:
				avg_brake_current = statistics.mean(avg_brake_current_array)
				avg_gen_rpm = statistics.mean(avg_gen_rpm_array)
				avg_gen_voltage = statistics.mean(avg_gen_voltage_array)
				avg_gen_amperage = statistics.mean(avg_gen_amperage_array)
				avg_gen_wattage = statistics.mean(avg_gen_wattage_array)

				avg_drv_rpm = statistics.mean(avg_drv_rpm_array)
				avg_drv_voltage = statistics.mean(avg_drv_voltage_array)
				avg_drv_amperage = statistics.mean(avg_drv_amperage_array)
				avg_drv_wattage = statistics.mean(avg_drv_wattage_array)

				if (avg_drv_wattage != 0):
					avg_efficiency = 100 * (avg_gen_wattage / avg_drv_wattage)
				else:
					avg_efficiency = 0

				print ("Efficiency: {:.1f}% | Brake Current: {:.2f}A | Generator: {:.0f}RPM, {:.1f}V, {:.2f}A, {:.1f}W | Driver: {:.0f}RPM, {:.1f}V, {:.2f}A, {:.1f}W".format(avg_efficiency, avg_brake_current, avg_gen_rpm, avg_gen_voltage, avg_gen_amperage, avg_gen_wattage, avg_drv_rpm, avg_drv_voltage, avg_drv_amperage, avg_drv_wattage))

				avg_brake_current_array = []
				avg_gen_rpm_array = []
				avg_gen_voltage_array = []
				avg_gen_amperage_array = []
				avg_gen_wattage_array = []
				avg_drv_rpm_array = []
				avg_drv_voltage_array = []
				avg_drv_amperage_array = []
				avg_drv_wattage_array = []

				next_display_time = time.time() + 0.25
				
				#if we hit the end of the power curve, exit
				if avg_gen_wattage < 0:
					break
				
			samples += 1

			#okay, write it to our csv...
		except AttributeError as e:
			continue
					

	driver.set_rpm(0)
	generator.set_brake_current(0)

	print ("Finished test with {} samples.".format(samples))


def characterise_generator_at_brake_current(driver, generator, test_current, start_rpm = 3000, end_rpm = 15000, test_duration = 30):

	print ("Test Current:", test_current)
	
	#init our test...
	driver.set_rpm(start_rpm)
	wait_for_rpm(driver, start_rpm)
	generator.set_brake_current(test_current)
	wait_for_rpm(driver, start_rpm)
	
	start_time = time.time()
	end_time = start_time + test_duration
	next_display_time = 0
	samples = 0

	avg_test_rpm_array = []
	avg_gen_rpm_array = []
	avg_gen_voltage_array = []
	avg_gen_amperage_array = []
	avg_gen_wattage_array = []
	avg_drv_rpm_array = []
	avg_drv_voltage_array = []
	avg_drv_amperage_array = []
	avg_drv_wattage_array = []
	
	while time.time() <= end_time:
		#set our brake current to be proportional based on time
		rpm_range = end_rpm - start_rpm
		test_rpm = start_rpm + rpm_range - rpm_range * ((end_time - time.time()) / test_duration)

		driver.set_rpm(int(test_rpm))

		try:
			measurements = generator.get_measurements()
			gen_rpm = measurements.rpm
			gen_voltage = measurements.v_in
			gen_amperage = -measurements.avg_input_current
			gen_wattage = gen_voltage * gen_amperage

			measurements = driver.get_measurements()
			drv_rpm = measurements.rpm
			drv_voltage = measurements.v_in
			drv_amperage = measurements.avg_input_current
			drv_wattage = drv_voltage * drv_amperage

			avg_test_rpm_array.append(test_rpm)
			avg_gen_rpm_array.append(gen_rpm)
			avg_gen_voltage_array.append(gen_voltage)
			avg_gen_amperage_array.append(gen_amperage)
			avg_gen_wattage_array.append(gen_wattage)
			avg_drv_rpm_array.append(drv_rpm)
			avg_drv_voltage_array.append(drv_voltage)
			avg_drv_amperage_array.append(drv_amperage)
			avg_drv_wattage_array.append(drv_wattage)

			
			if (drv_wattage != 0):
				efficiency = 100 * (gen_wattage / drv_wattage)
			else:
				efficiency = 0

			#do we want to display it?
			if time.time() > next_display_time:
				avg_test_rpm = statistics.mean(avg_test_rpm_array)
				avg_gen_rpm = statistics.mean(avg_gen_rpm_array)
				avg_gen_voltage = statistics.mean(avg_gen_voltage_array)
				avg_gen_amperage = statistics.mean(avg_gen_amperage_array)
				avg_gen_wattage = statistics.mean(avg_gen_wattage_array)

				avg_drv_rpm = statistics.mean(avg_drv_rpm_array)
				avg_drv_voltage = statistics.mean(avg_drv_voltage_array)
				avg_drv_amperage = statistics.mean(avg_drv_amperage_array)
				avg_drv_wattage = statistics.mean(avg_drv_wattage_array)

				if (avg_drv_wattage != 0):
					avg_efficiency = 100 * (avg_gen_wattage / avg_drv_wattage)
				else:
					avg_efficiency = 0

				print ("Efficiency: {:.1f}% | Target RPM: {:.0f} | Generator: {:.0f}RPM, {:.1f}V, {:.2f}A, {:.1f}W | Driver: {:.0f}RPM, {:.1f}V, {:.2f}A, {:.1f}W".format(avg_efficiency, avg_test_rpm, avg_gen_rpm, avg_gen_voltage, avg_gen_amperage, avg_gen_wattage, avg_drv_rpm, avg_drv_voltage, avg_drv_amperage, avg_drv_wattage))

				avg_test_rpm_array = []
				avg_gen_rpm_array = []
				avg_gen_voltage_array = []
				avg_gen_amperage_array = []
				avg_gen_wattage_array = []
				avg_drv_rpm_array = []
				avg_drv_voltage_array = []
				avg_drv_amperage_array = []
				avg_drv_wattage_array = []

				next_display_time = time.time() + 0.25
				
				#if we hit the end of the power curve, exit
				#if avg_gen_wattage < 0:
				#	break
				
			samples += 1

			#okay, write it to our csv...
		except AttributeError as e:
			continue
					

	#turn it off
	driver.set_rpm(0)
	generator.set_brake_current(0)

	print ("Finished test with {} samples.".format(samples))
	
def characterise_generator_old(driver, generator):
	#test_rpms = [5000, 10000]
	#test_brake_current = [1000, 2000, 3000, 4000, 5000]

	test_rpms = [10000]
	test_brake_current = [10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60]
	#test_brake_current = range(1, 30, 5)

	for target_rpm in test_rpms:
		#print ("Seeking to rpm:", target_rpm)
		generator.set_brake_current(0)
		driver.set_rpm(target_rpm)
		wait_for_rpm(driver, target_rpm)
		
		for brake_current in test_brake_current:
			#print ("Testing current:", brake_current)
			generator.set_brake_current(brake_current)
			wait_for_rpm(driver, target_rpm)

			#give it a few seconds to equalize
			time.sleep(2)

			avg_gen_rpm_array = []
			avg_gen_voltage_array = []
			avg_gen_amperage_array = []
			avg_gen_wattage_array = []
			avg_drv_rpm_array = []
			avg_drv_voltage_array = []
			avg_drv_amperage_array = []
			avg_drv_wattage_array = []

			end_time = time.time() + 5
			while(time.time() < end_time):

				measurements = generator.get_measurements()
				gen_rpm = measurements.rpm
				gen_voltage = measurements.v_in
				gen_amperage = abs(measurements.avg_input_current)
				gen_wattage = gen_voltage * gen_amperage

				avg_gen_rpm_array.append(gen_rpm)
				avg_gen_voltage_array.append(gen_voltage)
				avg_gen_amperage_array.append(gen_amperage)
				avg_gen_wattage_array.append(gen_wattage)
				
				#for name, value in vars(measurements).items():
				#	print(name, ":", value)

				measurements = driver.get_measurements()
				drv_rpm = measurements.rpm
				drv_voltage = measurements.v_in
				drv_amperage = measurements.avg_input_current
				drv_wattage = drv_voltage * drv_amperage

				avg_drv_rpm_array.append(drv_rpm)
				avg_drv_voltage_array.append(drv_voltage)
				avg_drv_amperage_array.append(drv_amperage)
				avg_drv_wattage_array.append(drv_wattage)
				
				efficiency = 100 * (gen_wattage / drv_wattage)

				#print ("{},{},{},{},{},{}".format(gen_rpm, gen_voltage, gen_amperage, drv_rpm, drv_voltage, drv_amperage))
				#print ("Generator: {:.0f}RPM, {:.1f}V, {:.2f}A, {:.1f}W | Driver: {:.0f}RPM, {:.1f}V, {:.2f}A, {:.1f}W | Efficiency: {:.1f}%".format(gen_rpm, gen_voltage, gen_amperage, gen_wattage, drv_rpm, drv_voltage, drv_amperage, drv_wattage, efficiency))

				time.sleep(0.5)

			avg_gen_rpm = statistics.mean(avg_gen_rpm_array)
			avg_gen_voltage = statistics.mean(avg_gen_voltage_array)
			avg_gen_amperage = statistics.mean(avg_gen_amperage_array)
			avg_gen_wattage = statistics.mean(avg_gen_wattage_array)

			avg_drv_rpm = statistics.mean(avg_drv_rpm_array)
			avg_drv_voltage = statistics.mean(avg_drv_voltage_array)
			avg_drv_amperage = statistics.mean(avg_drv_amperage_array)
			avg_drv_wattage = statistics.mean(avg_drv_wattage_array)

			avg_efficiency = 100 * (avg_gen_wattage / avg_drv_wattage)

			print ("Test RPM: {} | Brake Current: {}A | Generator: {:.0f}RPM, {:.1f}V, {:.2f}A, {:.1f}W | Driver: {:.0f}RPM, {:.1f}V, {:.2f}A, {:.1f}W | Efficiency: {:.1f}%".format(target_rpm, brake_current, avg_gen_rpm, avg_gen_voltage, avg_gen_amperage, avg_gen_wattage, avg_drv_rpm, avg_drv_voltage, avg_drv_amperage, avg_drv_wattage, avg_efficiency))

	driver.set_rpm(0)
	generator.set_brake_current(0)

	print ("Finished with test.")

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

def test_construct_parsing():
	binary = b'\x00\x05\x0260\x00@\x000\x00\x18PRAT70 \x00\x00\x00\x00'
	
	fields2 = Struct(
	    'comm_fw_version' / Int8ub,
		'fw_version_major' / Int8ub,
		'fw_version_minor' / Int8ub,
		'hw_name' / CString('utf8'),
    	'uuid' / Hex(BytesInteger(12))
	)

	pprint(vars(fields2))
	pprint(dir(fields2))
	pprint(fields2.subcons)
	for subcon in fields2.subcons:
		print (subcon.name)
	data = fields2.parse(binary)
	pprint(data)
	

if __name__ == '__main__':
	test_generator_motor()
