#!/usr/bin/python3

import RPi.GPIO as GPIO
import rpi_gpio
import adc
import time, os, atexit
import csv
import datetime
from datetime import date
import subprocess
from pathlib import Path
from servo import Servo 
#from ADSP9960 import Adsp9960, CLEAR, RED, GREEN, BLUE
from RGB_SENS_TEST import Adsp9960,I2C_FAILURE,CLEAR, RED, GREEN, BLUE


dir_path = os.path.dirname(os.path.realpath(__file__))
GPIO.setmode(GPIO.BCM)

#FW_FNAME = 'h1xmain-BootFw0.2_AppFw0.1.0.srec'
#FW_PATH = os.path.join(dir_path, 'jlink_fw', FW_FNAME)

#JLINK_SCRIPT_FNAME = '.'.join([Path(FW_FNAME).stem, 'jlink'])
#JLINK_SCPIRT_PATH = os.path.join(dir_path, 'jlink_fw', JLINK_SCRIPT_FNAME)

#JLINK_TEMPLATE_SCRIPT_FNAME = 'template_script.jlink'
#JLINK_TEMPLATE_SCPIRT_PATH = os.path.join(dir_path, 'jlink_fw', JLINK_TEMPLATE_SCRIPT_FNAME)

#NUM_OF_UUT = 1

Audible_Alarm_FLAG = False
FULL_PASS_FLAG=False
rgb_data = []

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

#======================== Test sequence: Calibration   ============================



#==================================================================================
#======================== Test sequence: Is Power Good ============================
def is_power_good():
    print('\n' + f' IS POWER GOOD UUT '.center(HEADER_WIDTH, '='))
    res = adc.check_adc_voltage(adc.POWER_GOOD_ADC)
    print(f'Power Good for UUT is {"OK" if res else "FAILED"}')
    return res
#==================================================================================

#======================== Test sequence: scan qr code ============================

def qr_code_csv():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    scanflag = True
    actual_weekday = 0
    DUT_SN = ""
    DUT_MAC= "00:00:00:00:00:00"
    PASS_FAIL_FLAG = ""
    CSV_FLAG = 'False'

    while scanflag:
        scanned_qr = input('\n'+'Scan DUT QR code to start the test sequence'+'\n')
        time.sleep(1) #added for terminal clarity
        print('\n'+ scanned_qr +'\n')
        time.sleep(1) #added for terminal clarity
        qr_split = []

        if "," in scanned_qr:
            qr_split = scanned_qr.split(',')
            print(qr_split)
            
            if len(qr_split) >= 2:
                DUT_SN = qr_split[0]
                DUT_MAC = qr_split[1]
        else:
            DUT_SN = scanned_qr

        if "AC" in qr_split or scanned_qr:
            scanned_isoweek = scanned_qr[4:6]
            #print('\n'+ scanned_isoweek)
            date_today = date.today()
            #print(date_today)
            iso_weekday = date_today.isocalendar() #Provide week following iso standard
            #print(iso_weekday[1])
            #print('\n'+scanned_isoweek)
            actual_weekday = iso_weekday[1]

            if actual_weekday == int(scanned_isoweek):
                scanflag = False
                #header = {'SerialNumber','BTMAC','TestResult'}
                header = {'SerialNumber':DUT_SN,'BTMAC':DUT_MAC,'TestResult':PASS_FAIL_FLAG}
                data = {'SerialNumber':DUT_SN,'BTMAC':DUT_MAC,'TestResult':PASS_FAIL_FLAG}
                #print(data)
                #saved_data=scanned_qr,Default_MAC,PASS_FAIL_FLAG
                
                DUT_FNAME = 'dut_w'+str(actual_weekday)+'.csv' 
                DUT_PATH = os.path.join(dir_path,'dut',DUT_FNAME)

                if os.path.isfile(DUT_PATH):
                    with open(DUT_PATH, "a", newline="") as file:
                        writer = csv.DictWriter(file, fieldnames=data.keys())
                        writer.writerow(data)
                        CSV_FLAG = 'True'
                        print('\n'+f"Data written to '{DUT_PATH}'."+'\n')
                else:
                    with open(DUT_PATH, 'w', newline='', encoding='utf-8') as file:
                        writer = csv.DictWriter(file, fieldnames=header)
                        writer.writeheader()
                        writer.writerow(data)
                        CSV_FLAG = 'True'
                        print('\n'+f"CSV file '{DUT_PATH}' created and data written."+'\n')

            if actual_weekday != int(scanned_isoweek):
                scanflag = False
                DUT_FNAME = 'dut_w'+str(scanned_isoweek)+'.csv' 
                DUT_PATH = os.path.join(dir_path,'dut',DUT_FNAME)

                header = {'SerialNumber':DUT_SN,'BTMAC':DUT_MAC,'TestResult':PASS_FAIL_FLAG}
                data = {'SerialNumber':DUT_SN,'BTMAC':DUT_MAC,'TestResult':PASS_FAIL_FLAG}

                if os.path.isfile(DUT_PATH):
                    with open(DUT_PATH, "a", newline="") as file:
                        writer = csv.DictWriter(file, fieldnames=data.keys())
                        writer.writerow(data)
                        CSV_FLAG = 'True'
                        print('\n'+f"Data written to '{DUT_PATH}'."+'\n')
                else:
                    with open(DUT_PATH, 'w', newline='', encoding='utf-8') as file:
                        writer = csv.DictWriter(file, fieldnames=header)
                        writer.writeheader()
                        writer.writerow(data)
                        CSV_FLAG = 'True'
                        print('\n'+f"CSV file '{DUT_PATH}' created and data written."+'\n')

    return CSV_FLAG,DUT_SN,DUT_MAC

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

#======================== Test sequence: Passthrough   ============================
# Activation of the 3 Nmos and read FB and gate
# If activation and fb signal change = test pass
# flag test status (pass or fail)

# GPIO's names: '7V5_COMP', '7V5_SSR_COMP', '7V5_FB_COMP', 'UUT_PWR_EN', 'MOS_USB_N_EN#' = 23, 'MOS_USB_P_EN#' = 24,
# 'MOS_LAMP_LR_EN#' = 25, 'SW_OUT_1', 'SW_OUT_2', 'FB_AND_GATE', 'LA_PWM', 'ADC_DRDY#', 'ADC_RST#'

def check_passthrough():
    #GPIO.setup(23,GPIO.OUT)
    #GPIO.setup(24,GPIO.OUT)
    #GPIO.setup(25,GPIO.OUT)
    #GPIO.setup(12,GPIO.IN)

    FB_AND_GATE = GPIO.input(12)
    counter = 0
    value = 0

    while value==0: # While not true, FB AND GATE does not output high level
        
        try:
            FB_AND_GATE = GPIO.input(12)

            if FB_AND_GATE == 0:
                print('\n'+ 'DRIVING PASSTHROUGH'+'\n')
                GPIO.output(23,0)
                time.sleep(0.1)
                FB_AND_GATE = GPIO.input(12)
                #print('\n'+ f'FB_AND_GATE:{value}'+'\n')
                GPIO.output(24,0)
                time.sleep(0.1)
                FB_AND_GATE = GPIO.input(12)
                #print('\n'+ f'FB_AND_GATE:{value}'+'\n')
                GPIO.output(25,0)
                FB_AND_GATE = GPIO.input(12)
                print('\n'+ f'FB_AND_GATE:{FB_AND_GATE}'+'\n')

                counter += 1

                if counter >= 5:
                    counter = 0
                    value = 1
                    print('\n'+'Passthrough test FAILED'+'\n')
                    PT_FLAG=False

            if FB_AND_GATE == 1:
                print('\n'+ f'FB_AND_GATE:{FB_AND_GATE}'+'\n')
                value=1
                PT_FLAG=True
                GPIO.output(23,1)
                GPIO.output(24,1)
                GPIO.output(25,1)

        except KeyboardInterrupt:
            GPIO.output(23,1)
            GPIO.output(24,1)
            GPIO.output(25,1)
            GPIO.cleanup()

    return PT_FLAG
  

#==================================================================================

#======================== Test sequence: Power Enable   ============================
# Activation of the Nmos and read FB and gate
# If activation and fb signal change = test pass
# flag test status (pass or fail)

# GPIO's names: '7V5_COMP', '7V5_SSR_COMP', '7V5_FB_COMP', 'UUT_PWR_EN', 'MOS_USB_N_EN#' = 23, 'MOS_USB_P_EN#' = 24,
# 'MOS_LAMP_LR_EN#' = 25, 'SW_OUT_1', 'SW_OUT_2', 'FB_AND_GATE', 'LA_PWM', 'ADC_DRDY#', 'ADC_RST#'

def check_power_enable():

    #GPIO.setup(4,GPIO.OUT)
    #GPIO.setup(17,GPIO.IN)
    #GPIO.setup(27,GPIO.IN)
    #GPIO.setup(22,GPIO.IN)

    WC_7V5 = GPIO.input(17)
    WC_SSR = GPIO.input(27)
    WC_FB = GPIO.input(22)

    counter=0
    PWR_EN_FLAG=False
    
    if WC_7V5 and WC_SSR and WC_FB == True:
        PWR_EN_FLAG = True

    #if WC_7V5 and WC_SSR and WC_FB == False:
    #    PWR_EN_FLAG = False

    while PWR_EN_FLAG==False:
        try:
            print('\n'+ 'DRIVING POWER'+'\n')
            GPIO.output(4,1)
            WC_7V5 = GPIO.input(17)
            WC_SSR = GPIO.input(27)
            WC_FB = GPIO.input(22)

            print(WC_7V5,WC_SSR,WC_FB)

            if WC_7V5 and WC_SSR and WC_FB == True:
                PWR_EN_FLAG = True

            if WC_7V5 and WC_SSR and WC_FB == False:
                GPIO.output(4,0)
                time.sleep(1)
                counter += 1
                print('\n'+'WC Failed RoF'+'\n')
                if counter >= 5:
                    counter = 0
                    value = 1
                    print('\n'+'Power Enable test FAILED'+'\n')
                    PWR_EN_FLAG=True

        except KeyboardInterrupt:
            GPIO.output(4,0)
            GPIO.cleanup()

    return PWR_EN_FLAG
  

#==================================================================================

#============================  Linear actuator test  ===============================
# ipwm = 3 or ipwm = 11
def linear_actuator():
    #GPIO.setup(13,GPIO.OUT)
    pwm = GPIO.PWM(13,50)
    pwm.start(0)
    
    PAIRING_REQUEST_FLAG=1
    try:
        while PAIRING_REQUEST_FLAG==1:
            if PAIRING_REQUEST_FLAG==1:
                pwm.ChangeDutyCycle(10)
                #read LED should be blue
                #if led is blue -> pairing flag =0
                print('Linear_Actuator is now on')
                time.sleep(1)
                PAIRING_REQUEST_FLAG=0

            if PAIRING_REQUEST_FLAG==0:
                pwm.ChangeDutyCycle(2)
                time.sleep(1)
                #pwm.stop()
                print('Linear_Actuator is now off')

    except KeyboardInterrupt:
        pwm.stop()

#==================================================================================            

#=========================== Ambient light sensor test =============================

def rgb_sensor():
    # Create an instance of the Adsp9960 class
    sensor = Adsp9960()
    RGB_SENSOR_FLAG=False

    # Enable color readings
    if sensor.enable_color_readings() == I2C_FAILURE:
        print("Failed to enable color readings.")
        return

    # Specify the expected color and intensity
    expected_color = [RED,GREEN,BLUE]
    expected_intensity = 100

    # Check if the expected color meets the expected intensity
    if sensor.read_expected_color(expected_color[0], expected_intensity):
        print("The intensity of the color is equal to or greater than the expected intensity.")
        RGB_SENSOR_FLAG = True
    else:
        print("The intensity of the color is less than the expected intensity.")
    
    return RGB_SENSOR_FLAG


def rgb_all():
    # Create an instance of the Adsp9960 class
    sensor = Adsp9960()

    # Enable color readings
    if sensor.enable_color_readings() == I2C_FAILURE:
        print("Failed to enable color readings.")
        return

    # Read and print all colors
    colors = sensor.read_colors()
    #colorlight = sensor.check_for_colored_light(RED,0)

    if colors == I2C_FAILURE:
        print("Failed to read color data.")
        return

    #time.sleep(0.1) # add clarity in terminal
    #print("Red: ", colors[RED])
    #print("Green: ", colors[GREEN])
    #print("Blue: ", colors[BLUE])
 
    #time.sleep(0.1) # add clarity in terminal
    choice = input('Enter color to be tested, red, green or blue')
    while True:
        try:
            colors = sensor.read_colors()
            print(f'Red: {colors[RED]}, Green: {colors[GREEN]}, Blue: {colors[BLUE]}')
            rgb_data.append([colors[RED], colors[GREEN], colors[BLUE]])
            time.sleep(0.1)  # pause for 100 ms

        except KeyboardInterrupt:
            with open('rgb_data_'+str(choice)+'.csv', 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerows(rgb_data)
            GPIO.cleanup()
            return

    # Print out the color readings
    # print("Red: ", colors[RED])
    # print("Green: ", colors[GREEN])
    # print("Blue: ", colors[BLUE])

#================================================================================== 

#======================== Test sequence: Listen   ============================
def listen_Buzzer():
    MAX_DBA=True
    DBA_TH=90
    Audible_Alarm_FLAG = False
    try:
        while(MAX_DBA):
            sound_level = check_mic_level()
            print('\n'+f'{sound_level} dBA'+'\n')
            if sound_level >= DBA_TH:
                time.sleep(1)
                print('\n'+f'TEST PASSED {sound_level} dBA'+'\n')
                MAX_DBA=False
                Audible_Alarm_FLAG = True
        
            print(Audible_Alarm_FLAG)

        return Audible_Alarm_FLAG    
    
    except KeyboardInterrupt:
        GPIO.cleanup()
        

#==================================================================================
#======================== Test sequence: Detection Switches   ============================
# Read the 2 reed switches, if the operator removes the top section while tests are ongoing,
# The test sequence must be canceled.
def Detection_Switches():
    #GPIO.setup(7, GPIO.IN)
    #GPIO.setup(8, GPIO.IN)

    SW1 = GPIO.input(7)
    SW2 = GPIO.input(8)
    result = SW1 and SW2

    print(f'SW1: {SW1}\nSW2: {SW2}\nResult: {result}\n')
    time.sleep(3)
    
    ENCLOSURE_STATE_FLAG = result

    if not result:
        print('Test Canceled\n')

    return ENCLOSURE_STATE_FLAG

#==================================================================================
#======================== Test Manager ============================================

def test_manager(PT_FLAG,Audible_Alarm_FLAG,ENCLOSURE_STATE_FLAG,RGB_SENSOR_FLAG,PWR_EN_FLAG):

    return

#==================================================================================

if __name__ == '__main__':
    '''if not is_usb_jlink_connected():
        print('ERROR: Not found USB JLink device')
        exit(1)'''
    x=0
    
    is_power_good()
    CSV_STATUS = qr_code_csv()
    print(CSV_STATUS[0])
  
    while(Detection_Switches()):
        
        if CSV_STATUS[0] == 'True':
            check_passthrough()
            check_power_enable()
            check_current_sensor()
            for x in range(5):
                #rgb_sensor()
                rgb_all()
                #linear_actuator()
                #check_mic_level()

            FULL_PASS_FLAG=listen_Buzzer()
        if FULL_PASS_FLAG==True:
            print('\n'+'TEST PASSED'+'\n')
            print('\n'+'TEST PASSED'+'\n')
            print('\n'+'TEST PASSED'+'\n')
            print('\n'+'TEST PASSED'+'\n')
            exit
    '''
    while Detection_Switches():
    # This code will run as long as Detection_Switches() returns True
        rgb_sensor()
        rgb_all()
        if CSV_STATUS[0] == 'True':
            check_passthrough()
            check_power_enable()
            check_current_sensor()
            linear_actuator()
            check_mic_level()
    '''