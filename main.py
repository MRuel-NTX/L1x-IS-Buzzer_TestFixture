#!/usr/bin/python3

import rpi_gpio
import adc
import time, os, atexit
import datetime
import subprocess
from pathlib import Path
from servo import Servo 
from adsp9960 import Adsp9960, CLEAR, RED, GREEN, BLUE


dir_path = os.path.dirname(os.path.realpath(__file__))

#FW_FNAME = 'h1xmain-BootFw0.2_AppFw0.1.0.srec'
#FW_PATH = os.path.join(dir_path, 'jlink_fw', FW_FNAME)

#JLINK_SCRIPT_FNAME = '.'.join([Path(FW_FNAME).stem, 'jlink'])
#JLINK_SCPIRT_PATH = os.path.join(dir_path, 'jlink_fw', JLINK_SCRIPT_FNAME)

#JLINK_TEMPLATE_SCRIPT_FNAME = 'template_script.jlink'
#JLINK_TEMPLATE_SCPIRT_PATH = os.path.join(dir_path, 'jlink_fw', JLINK_TEMPLATE_SCRIPT_FNAME)

#NUM_OF_UUT = 1

HEADER_WIDTH = 100

def exit_handler():
    print('\n' + ''.center(HEADER_WIDTH, '='))

atexit.register(exit_handler)

#==================================================================================
# create required file structure before start
# make 'log' folder in the currect working folder
LOG_PATH = os.path.join(dir_path, 'log')
if not os.path.exists(LOG_PATH):
    os.makedirs(LOG_PATH)
    
#========================= ADCs check presence section ============================
print('\n' + ' CHECK AVAILABILITY FOR ADCs '.center(HEADER_WIDTH, '='))
adc.load_adc_conf()
res = adc.check_availability()  # to check presence ADCs on i2c bus -> this is a sign that TJ is power ON ?!
if not res:
    print('TJ Power is FAILED, fix it (check power, cable connections, GPIOs configuration, etc.) and try again') #?! or just ADC not found
    exit(3)
else: print('ADCs in the system: TJ Power is OK')

#============================== GPIO init section =================================
print('\n' + ' PREPARE GPIOs '.center(HEADER_WIDTH, '='))
rpi_gpio.load_gpio_map()
gpio = rpi_gpio.RPI_GPIO()

def validate_gpios_config_init(gpio):  # check actual GPIO's values after first configuration
    # GPIO's names: '7V5_COMP', '7V5_SSR_COMP', '7V5_FB_COMP', 'UUT_PWR_EN', 'MOS_USB_N_EN#', 'MOS_USB_P_EN#',
    # 'MOS_LAMP_LR_EN#', 'SW_OUT_1', 'SW_OUT_2', 'FB_AND_GATE', 'LA_PWM', 'ADC_DRDY#', 'ADC_RST#'
    try:
        # get values for Output GPIOs
        gpios_out = {'UUT_PWR_EN': 0, 'MOS_USB_N_EN#': 1, 'MOS_USB_P_EN#': 1, 'MOS_LAMP_LR_EN#': 1, 'LA_PWM': 0, 'ADC_RST#': 1}
        for it in gpios_out.items():
            assert it[1] == gpio.get_gpio_value(it[0]), f'{it[0]}  should be {it[1]}'

        # get values for Input GPIOs
        gpios_in = ('7V5_COMP', '7V5_SSR_COMP', '7V5_FB_COMP', 'SW_OUT_1', 'SW_OUT_2', 'FB_AND_GATE', 'ADC_DRDY#')
        for it in gpios_in: gpio.get_gpio_value(it)
    except Exception as ex:
        print('FAILED:', ex)
        return False

    return True

res = validate_gpios_config_init(gpio)
if not res:
    print('GPIOs initialization is FAILED, fix it (check power, cable connections, PRi GPIO configuration, etc.) and try again')
    exit(3)
else: print('GPIOs initialization is OK')


#============================  Linear actuator test  ===============================
actuator = Servo(gpio.gpio_map["LA_PWM"]['gpio'])
actuator.set_duty_cycle_range(2.5, 13)
actuator.set_angle(180)
time.sleep(3)
actuator.set_angle(10)

#=========================== Ambient light sensor test =============================
light_sensor = Adsp9960()
light_sensor.enable_color_readings()
while(1):
    if light_sensor.check_for_colored_lght(RED, 10):
        print(f"Found RED light")
        
    if light_sensor.check_for_colored_lght(GREEN, 10):
        print(f"Found GREEN light")
        
    if light_sensor.check_for_colored_lght(BLUE, 10):
        print(f"Found BLUE light")

    time.sleep(0.5)