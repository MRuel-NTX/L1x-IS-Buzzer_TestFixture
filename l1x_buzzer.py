#!/usr/bin/python3

import RPi.GPIO as GPIO
import rpi_gpio
import adc
import jlink
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


Audible_Alarm_FLAG = False
FULL_PASS_FLAG=False
rgb_data = []
DUT_SN = ""
DUT_MAC= "00:00:00:00:00:00"
colors= ''
PAIRED_FLAG=False

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

#====================== Test sequence: JLink programming ==========================
def jlink_programming():
    is_need_jlink_flash = input('Is need to do jlink programming?[Y/n]:').lower()
    if 'y' == is_need_jlink_flash:
        if jlink.is_usb_jlink_connected():
            jlink.jlink_programming()
#==================================================================================

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


    DUT_MAC= "00:00:00:00:00:00"
    PASS_FAIL_FLAG = ""
    CSV_FLAG = False

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
                        CSV_FLAG = True
                        print('\n'+f"Data written to '{DUT_PATH}'."+'\n')
                else:
                    with open(DUT_PATH, 'w', newline='', encoding='utf-8') as file:
                        writer = csv.DictWriter(file, fieldnames=header)
                        writer.writeheader()
                        writer.writerow(data)
                        CSV_FLAG = True
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
                        CSV_FLAG = True
                        print('\n'+f"Data written to '{DUT_PATH}'."+'\n')
                else:
                    with open(DUT_PATH, 'w', newline='', encoding='utf-8') as file:
                        writer = csv.DictWriter(file, fieldnames=header)
                        writer.writeheader()
                        writer.writerow(data)
                        CSV_FLAG = True
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
    i=0
    PAIRED_FLAG=False
    changestep='1'
    PAIRING_REQUEST_FLAG=1
    print('before try linear actuator')
    

    #read LED should be blue
    #if led is blue -> pairing flag =0
    while PAIRED_FLAG==False:
        try:
            rgb_all()
            time.sleep(1)
            if RED and PAIRED_FLAG==False:
                pwm.ChangeDutyCycle(2)
                #time.sleep(1)
                i += 1
                changestate=input('enter y if blue LED')
                if i>=50:
                    i=0
            if changestate=='y':
                PAIRED_FLAG=True
                print('\n'+f'{BLUE}'+'\n')
                pwm.ChangeDutyCycle(11)
                pwm.stop()
                #if PAIRED_FLAG==True:
                #    pwm.start(0)


        except KeyboardInterrupt:
            pwm.stop()

    

    '''
    try:
        while PAIRING_REQUEST_FLAG==1:
            pwm.ChangeDutyCycle(10)
                #read LED should be blue
                #if led is blue -> pairing flag =0
            print('\n'+'Linear_Actuator is now on'+'\n')
            if
                time.sleep(1)
                PAIRING_REQUEST_FLAG=0

            if PAIRING_REQUEST_FLAG==0:
                pwm.ChangeDutyCycle(2)
                time.sleep(1)
                #pwm.stop()
                print('Linear_Actuator is now off')

    except KeyboardInterrupt:
        pwm.stop()
    '''
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

    #choice = input('Enter color to be tested, red, green or blue')

    #while True:
    try:
        colors = sensor.read_colors()
        print(f'Red: {colors[RED]}, Green: {colors[GREEN]}, Blue: {colors[BLUE]}')
        rgb_data.append([colors[RED], colors[GREEN], colors[BLUE]])
        time.sleep(0.01)  # pause for 10 ms
        return(colors)
    
    except KeyboardInterrupt:
            #with open('rgb_data_'+str(choice)+'.csv', 'w', newline='') as file:
            #    writer = csv.writer(file)
            #    writer.writerows(rgb_data)
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
    DBA_TH=110
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



'''
### Test of input selected DBA thresh, will print the selected dBA level. Will run the listen mic until dBA th is acheived.


def listen_Buzzer(DBA_TH):
    MAX_DBA=True
    Audible_Alarm_FLAG = False
    print(f'Selected dBa level: {DBA_TH}')
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
        GPIO.cleanup()'''

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
    PAIRED_FLAG=False
    

    is_power_good() #Power of Test PCBA
    check_passthrough() #Unit is connected to Test PCBA
    CSV_STATUS = qr_code_csv() #Unit ID is scanned (should save data)
    print(CSV_STATUS[0])
  
    jlink_programming() # ask and if need - do with default FW

    while True:
    #while(Detection_Switches()): ######need to be added back
        
        if CSV_STATUS[0] == True:
            check_power_enable()
            linear_actuator()
            listen_Buzzer()
            rgb_all()



            '''
            yn=input('\n'+'Please Turn on the Unit'+'\n'+'When the unit is powered, enter Y'+'\n'+'To exit, enter N')
            #check_passthrough()
            if yn == 'y' or 'Y':
                print("=========================== Programming Step ======================================")
                programmed=input('\n'+'Is the programming done?'+'\n'+'Enter Y when completed'+'\n'+'To Exit, enter N')

                #check_power_enable()
                #check_current_sensor()
                
            for x in range(5):
                #rgb_sensor()
                rgb_all()
                linear_actuator()
                #check_mic_level()

                FULL_PASS_FLAG=listen_Buzzer()
            if FULL_PASS_FLAG==True:
                print('\n'+'TEST PASSED'+'\n')
                print('\n'+'TEST PASSED'+'\n')
                print('\n'+'TEST PASSED'+'\n')
                print('\n'+'TEST PASSED'+'\n')
                exit
    
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