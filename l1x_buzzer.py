#!/usr/bin/python3

import rpi_gpio
import adc
import jlink
import time, os, atexit
import datetime
import subprocess
from pathlib import Path


dir_path = os.path.dirname(os.path.realpath(__file__))

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
#==================================================================================

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
#==================================================================================

#======================== Test sequence: Is Power Good ============================
def is_power_good():
    print('\n' + f' IS POWER GOOD UUT '.center(HEADER_WIDTH, '='))
    res = adc.check_adc_voltage(adc.POWER_GOOD_ADC)
    print(f'Power Good for UUT is {"OK" if res else "FAILED"}')
    return res

def check_current_sensor():  # now applicable for L1x buzzer
    ''' for current sensor using AIN2 on ADC, from datasheet - base level VOUT voltage without current - 1.65V\n
        max possible VOUT of sensor - 3.3V (by our schematic); and delta - 400mV / 1A\n
        return: current in A '''
    delta = 0.4   # V/A
    res = adc.get_adc_voltage(adc.POWER_GOOD_ADC)
    Vout  = res[2]        # res[2] - value measured on AIN2
    Vbase = res[0] * 0.5  # res[0] - it should be 3.3V (VS, this power apply for the Current Sensor) and measure on AIN0 of ADC; VS*0.5 - from datasheet
    current = round((Vout - Vbase) / 0.4, 3)
    print(f'Current Sensor: VOUT [{Vout} V], current [{current} A]')
    return current

def check_mic_level():  # now applicable only for L1x buzzer
    ''' for mic level using AIN3 on ADC, from datasheet range should be 0.6 - 2.6 V\n
        the function is linear (y = 50*x); so available sound level range 30 - 130 dBA\n
        for calculate actual dBA level - just multiply actual Voltage by 50\n
        return: sound level in dBA '''
    res = adc.get_adc_voltage(adc.POWER_GOOD_ADC)
    Vout  = res[3]        # res[3] - value measured on AIN3
    sound_level = int(50 * Vout)
    print(f'Mic sound level: [{sound_level} dBA]')
    return sound_level

#==================================================================================
#====================== Test sequence: JLink programming ==========================

if __name__ == '__main__':
    '''if not is_usb_jlink_connected():
        print('ERROR: Not found USB JLink device')
        exit(1)'''
    is_power_good()
    check_current_sensor()
    check_mic_level()
    is_need_jlink_flash = input('Is need to do jlink programming[Y/n]:').lower()
    if is_need_jlink_flash == 'y':
        if jlink.is_usb_jlink_connected():
            jlink.jlink_programming()  # will do jlink programming with a default FW for the buzzer