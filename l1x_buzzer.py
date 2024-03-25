#!/usr/bin/python3

import rpi_gpio
import adc
import time, os, atexit
import datetime
import subprocess
from pathlib import Path


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

'''# create jlink script from template if not exist yet for specified FW
FW_PATH_REPLACE_MARKER = 'FW_PATH'
if not os.path.exists(JLINK_SCPIRT_PATH):
    with open(JLINK_TEMPLATE_SCPIRT_PATH, 'r') as jlink_script_template:
        script = jlink_script_template.readlines()
        with open(JLINK_SCPIRT_PATH, 'w') as jlink_script:
            for line in script:
                if FW_PATH_REPLACE_MARKER in line:
                    lkw = line.strip().split()
                    lkw[1] = FW_PATH   # it because line should be as: 'loadfile FW_PATH 0x00000000'
                    line = ' '.join(lkw) + '\n'
                jlink_script.write(line)'''

# check on presence USB JLink programmator
#def is_usb_jlink_connected():
#    ''' in this version function we suppose using only one connected USB JLink device '''
#    print('\n' + ' USB JLINK CHECK PRESENCE '.center(HEADER_WIDTH, '='))
#    response = subprocess.run('echo exit | JLinkExe -NoGui 1', shell=True, capture_output=True)
#    str_resp = response.stdout.decode('utf-8')
#
#    USB_OK = 'USB...O.K.'
#    USB_FAILED = 'USB...FAILED'
#    SN = 'S/N:'
#    # check on 'USB...O.K.' or 'USB...FAILED'
#    # if 'USB...O.K.' then get S/N (serial number)
#    res = False
#    if USB_OK in str_resp:
#        JLINK_USB_SN = None
#        for l in str_resp.splitlines():
#            if l.startswith(SN):
#                JLINK_USB_SN = l.split()[1]  # split string with S/N and get the second item with value
#                res = True
#                break
#        print('OK: USB JLink found, S/N:', JLINK_USB_SN)
#    elif USB_FAILED in str_resp:
#        print('ERROR: USB JLink not found')
#    else:
#        print('ERROR: Unknown status for USB JLink')
#
#    return res

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

#====================== Test sequence: JLink programming ==========================
#==================================================================================

# Read LATCH_PANEL_DETECT#: if 1 - no UUT==> EXP_RESET# is set at '0' ==> IOExp pins are input tristate
# If LATCH_PANEL_DETECT# == 1, the UUT is not present. Test Jig set the EXP_RESET#=0 that put back all IOExp pins in input mode
'''def is_panel_detected():  # check on presence for the UUTs panel
    print('\n' + ' CHECK UUTs PANEL PRESENCE '.center(HEADER_WIDTH, '='))
    #exp_reset_ = gpio.get_gpio_value('EXP_RESET#')
    latch_panel_detect_ = gpio.get_gpio_value('LATCH_PANEL_DETECT#')  # if 0 - UUTs panel is present
    is_ready = not latch_panel_detect_
    print(f'UUTs panel detection is {"OK" if is_ready else "FAILED"}')
    #gpio.set_gpio_value('EXP_OE#', 0)  # for activate output for IOExp
    return is_ready
'''
# setup all required gpio and IOExp pins for correct JLink programming of specified UUT number
#def prepare_uut_for_jlink_programming(uut_id):
#    ''' uut_id - it's a integer value from 1 to 4, which specify uut number '''
#    print('\n' + f' PREPARE UUT[{uut_id}] FOR JLINK PROGRAMMING '.center(HEADER_WIDTH, '='))
#    if uut_id not in range(1,5):
#        print(f'UUT id[{uut_id}] is not correct')
#        return False

#    print(f'Select UUT[{uut_id}] and power ON it')
#    exp.set_pin('PO', f'UUT{uut_id}_PWR_EN', 0)      # power off for UUT<uut_id>
#    gpio.set_gpio_value('MUX_EN', 0)                 # set MUX_EN to 0 for pure setup setup MUX_A1 and MUX_A0 values

    # LUT - look up tables for MUX and USB A1_A0 values. First tuple element is empty just for stub of indexing
#    A1_A0     = ((), (1,1), (1,0), (0,0), (0,1))
    #USB_A1_A0 = ((), (1,1), (0,1), (0,0), (1,0))  # no need to setup USB mux pins for JLink programming
    #exp.set_bucket_pins('PO', {'USB_A1': USB_A1_A0[uut_id][1], 'USB_A0': USB_A1_A0[uut_id][0]})  # set values for pins USB_A1 and USB_A0 of IOExp

#    gpio.set_gpio_value('MUX_A1', A1_A0[uut_id][1])  # set uut_id number through set values for MUX_A1 and MUX_A0
#    gpio.set_gpio_value('MUX_A0', A1_A0[uut_id][0])
#    gpio.set_gpio_value('MUX_EN', 1)   # set MUX_EN to 1 for activate actual MUX_A1 and MUX_A0 values

#    exp.set_pin('PO', f'UUT{uut_id}_PWR_EN', 1)  # power on for UUT<uut_id>
#    time.sleep(0.5)
#    gpio.set_gpio_value('EXP_OE#', 0)            # set 0 to EXP_OE# for activate IOExp output
#    return True

# perform jlink programming - call external segger command tool for running script
#def jlink_programming(id, script_path=JLINK_SCPIRT_PATH):
#    ''' id - is integer of actual UUT number\n
#        fw_path - it's a string with a full path on jlink script\n
#        jlink script consist all required parameters: device, frequency, name of srec file and programming address;\n
#        and shoud run in a segger command tool '''
#    print('\n' + f' JLINK PROGRAMMING UUT[{id}] '.center(HEADER_WIDTH, '='))
#    if not os.path.isfile(script_path):
#        print(f'JLink script {script_path} not found')
#        return False
#
#    dt = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
#    LOG_FNAME = os.path.join(LOG_PATH, f'JLink_UUT{id}_{dt}.log')
#    print(f'Run jlink scrpt:\n  {script_path}')
#    # run JLinkExe program without GUI and don't output log of execution but save it in the file
#    # JLink tool feature: '-Log', LOG_FNAME; it produce a big detailed log
#    response = subprocess.run(['JLinkExe', '-NoGui', '1', '-CommandFile', script_path], shell=False, capture_output=True)
#
#    with open(LOG_FNAME, 'w') as jlog:  # save jlink output to log file
#        jlog.write(response.stdout.decode('utf-8'))
#
#    res = True if response.returncode == 0 else False
#    print(f'JLink programming for UUT[{id}] is {"OK" if res else "FAILED"}')
#    print(f'For details see log in the file:\n  {LOG_FNAME}')
#    return res

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


if __name__ == '__main__':
    '''if not is_usb_jlink_connected():
        print('ERROR: Not found USB JLink device')
        exit(1)'''
    is_power_good()
    check_current_sensor()
    check_mic_level()