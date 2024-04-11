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
    
FW_FNAME = 'mcuboot_app_merged_0.1.3+1.hex'
FW_PATH = os.path.join(dir_path, 'jlink_fw', FW_FNAME)

JLINK_SCRIPT_FNAME = '.'.join([Path(FW_FNAME).stem, 'jlink'])
JLINK_SCPIRT_PATH = os.path.join(dir_path, 'jlink_fw', JLINK_SCRIPT_FNAME)

JLINK_TEMPLATE_SCRIPT_FNAME = 'template_script.jlink'
JLINK_TEMPLATE_SCPIRT_PATH = os.path.join(dir_path, 'jlink_fw', JLINK_TEMPLATE_SCRIPT_FNAME)

    
def is_usb_jlink_connected():
   ''' in this version function we suppose using only one connected USB JLink device '''
   print('\n' + ' USB JLINK CHECK PRESENCE '.center(HEADER_WIDTH, '='))
   response = subprocess.run('echo exit | JLinkExe -NoGui 1', shell=True, capture_output=True)
   str_resp = response.stdout.decode('utf-8')

   USB_OK = 'USB...O.K.'
   USB_FAILED = 'USB...FAILED'
   SN = 'S/N:'
   # check on 'USB...O.K.' or 'USB...FAILED'
   # if 'USB...O.K.' then get S/N (serial number)
   res = False
   if USB_OK in str_resp:
       JLINK_USB_SN = None
       for l in str_resp.splitlines():
           if l.startswith(SN):
               JLINK_USB_SN = l.split()[1]  # split string with S/N and get the second item with value
               res = True
               break
       print('OK: USB JLink found, S/N:', JLINK_USB_SN)
   elif USB_FAILED in str_resp:
       print('ERROR: USB JLink not found')
   else:
       print('ERROR: Unknown status for USB JLink')

   return res

def jlink_programming(script_path=JLINK_SCPIRT_PATH):
   ''' id - is integer of actual UUT number\n
       fw_path - it's a string with a full path on jlink script\n
       jlink script consist all required parameters: device, frequency, name of srec file and programming address;\n
       and shoud run in a segger command tool '''
   print('\n' + f' JLINK PROGRAMMING '.center(HEADER_WIDTH, '='))
   if not os.path.isfile(script_path):
       print(f'JLink script {script_path} not found')
       return False

   dt = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
#    LOG_FNAME = os.path.join(LOG_PATH, f'JLink_UUT{id}_{dt}.log')
   print(f'Run jlink scrpt:\n  {script_path}')
   # run JLinkExe program without GUI and don't output log of execution but save it in the file
   # JLink tool feature: '-Log', LOG_FNAME; it produce a big detailed log
   response = subprocess.run(['JLinkExe', '-NoGui', '1', '-CommandFile', script_path], shell=False, capture_output=True)

#    with open(LOG_FNAME, 'w') as jlog:  # save jlink output to log file
#        jlog.write(response.stdout.decode('utf-8'))

   res = True if response.returncode == 0 else False
   print(f'JLink programming is {"OK" if res else "FAILED"}')
#    print(f'For details see log in the file:\n  {LOG_FNAME}')
   return res

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
def qr_scan():
    DUT_SN = " "
    DUT_MAC = "00:00:00:00:00:00"
    scanned_qr = input('\n [+] Scan DUT QR code to start the test sequence \n')
    time.sleep(1) #added for terminal clarity
    print("SERIAL NUMBER : "+ scanned_qr)
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

        return [1, DUT_SN, DUT_MAC, scanned_isoweek]
    else:
        print(" [-] ERROR during scanning")
        exit(3)
        return [0,0,0]

def find_SN_in_file(file_name, SN):
    with open(file_name, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['SerialNumber'] == SN:
                return True
    return False

def add_csv_log(SN, MAC, isoweek, RESULTS):
    dir_path = os.path.dirname(os.path.realpath(__file__))

    DUT_FNAME = 'dut_w'+str(isoweek)+'.csv' 
    DUT_PATH = os.path.join(dir_path,'dut',DUT_FNAME)
    
    DATE_TIME = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    data = {'Date/Time':DATE_TIME, 'SerialNumber':SN,'BTMAC':MAC,'TestResults':format(RESULTS, "07b") }
    
    if not os.path.isfile(DUT_PATH):
        with open(DUT_PATH, 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=data)
            writer.writeheader()

    with open(DUT_PATH, "a", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=data.keys())
        writer.writerow(data)
        CSV_FLAG = True
        print(f"\n [+] Data written to '{DUT_PATH}'.\n")
    

def check_current_sensor():  # now applicable for L1x buzzer
    ''' for current sensor using AIN2 on ADC, from datasheet - base level VOUT voltage without current - 1.65V\n
        max possible VOUT of sensor - 3.3V (by our schematic); and delta - 400mV / 1A\n
        return: current in A '''
    delta = 0.4   # V/A
    res = adc.get_adc_voltage(adc.POWER_GOOD_ADC)
    Vout  = res[2]        # res[2] - value measured on AIN2
    Vbase = res[0] * 0.5  # res[0] - it should be 3.3V (VS, this power apply for the Current Sensor) and measure on AIN0 of ADC; VS*0.5 - from datasheet
    current = round((Vout - Vbase) / 0.4, 3)
    print(f' [>] Current Sensor: VOUT [{Vout} V], current [{current} A]')
    return current

def check_mic_level():  # now applicable only for L1x buzzer
    ''' for mic level using AIN3 on ADC, from datasheet range should be 0.6 - 2.6 V\n
        the function is linear (y = 50*x); so available sound level range 30 - 130 dBA\n
        for calculate actual dBA level - just multiply actual Voltage by 50\n
        return: sound level in dBA '''
    res = adc.get_adc_voltage(adc.POWER_GOOD_ADC)
    Vout  = res[3]        # res[3] - value measured on AIN3
    sound_level = int(50 * Vout)
    print(f' [>] Mic sound level: [{sound_level} dBA]')
    return sound_level

#==================================================================================

#======================== Test sequence: Passthrough   ============================
# Activation of the 3 Nmos and read FB and gate
# If activation and fb signal change = test pass
# flag test status (pass or fail)

# GPIO's names: '7V5_COMP', '7V5_SSR_COMP', '7V5_FB_COMP', 'UUT_PWR_EN', 'MOS_USB_N_EN#' = 23, 'MOS_USB_P_EN#' = 24,
# 'MOS_LAMP_LR_EN#' = 25, 'SW_OUT_1', 'SW_OUT_2', 'FB_AND_GATE', 'LA_PWM', 'ADC_DRDY#', 'ADC_RST#'

def check_passthrough():
    FB_AND_GATE = GPIO.input(12)
    counter = 0
    value = 0

    while value==0: # While not true, FB AND GATE does not output high level
        
        try:
            FB_AND_GATE = GPIO.input(12)
            print(" [.] Doing: Passthrough test")

            if FB_AND_GATE == 0:
                #print('\n DRIVING PASSTHROUGH \n')
                GPIO.output(23,0)
                time.sleep(0.1)
                FB_AND_GATE = GPIO.input(12)
                #print('\n f'FB_AND_GATE:{value} \n')
                GPIO.output(24,0)
                time.sleep(0.1)
                FB_AND_GATE = GPIO.input(12)
                #print('\n f'FB_AND_GATE:{value} \n')
                GPIO.output(25,0)
                FB_AND_GATE = GPIO.input(12)
                #print(f'\n FB_AND_GATE:{FB_AND_GATE} \n')

                counter += 1

                if counter >= 5:
                    counter = 0
                    value = 1
                    print(' [-] FAILED Passthrough test  ')
                    PT_FLAG=False

            if FB_AND_GATE == 1:
                print(f'\n [+] TEST PASSED: Passthrough ')
                #print(f'\n FB_AND_GATE:{FB_AND_GATE} \n')
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
def power_enable():
    print('\n [>] DRIVING POWER ')
    GPIO.output(4,1)
    time.sleep(1)
    
def power_disable():
    print('\n [>] REMOVING POWER ')
    GPIO.output(4,0)
    time.sleep(1)
    
    
def check_power_enable():
    WC_7V5 = GPIO.input(17)
    WC_SSR = GPIO.input(27)
    WC_FB = GPIO.input(22)

    counter=0
    PWR_EN_FLAG=False
    
    if WC_7V5 and WC_SSR and WC_FB == True:
        PWR_EN_FLAG = True

    while PWR_EN_FLAG==False:
        try:

            WC_7V5 = GPIO.input(17)
            WC_SSR = GPIO.input(27)
            WC_FB = GPIO.input(22)

            if WC_7V5 and WC_SSR and WC_FB == True:
                PWR_EN_FLAG = True

            if WC_7V5 and WC_SSR and WC_FB == False:
                GPIO.output(4,0)
                time.sleep(1)
                counter += 1
                if counter >= 5:
                    counter = 0
                    value = 1
                    print(' [>] FAILED Power Enable test ')
                    PWR_EN_FLAG=True

        except KeyboardInterrupt:
            GPIO.output(4,0)
            GPIO.cleanup()

    return PWR_EN_FLAG
  

#==================================================================================

#============================  Linear actuator test  ===============================
# ipwm = 3 or ipwm = 11
def pairing_sequence():
    sensor = Adsp9960()
    sensor.enable_color_readings()
    #GPIO.setup(13,GPIO.OUT)
    #pwm = GPIO.PWM(13,50)
    #pwm.start(11)
    RESTART = False
    IS_PAIRED = False
    PAIRING = False
    
    while not IS_PAIRED:
        if RESTART:
            print(" [-] Paired failed, trying again")
            time.sleep(1)
        input(" [>] Press enter to start pairing ")
        pwm.start(11)
        pwm.ChangeDutyCycle(11)
        time.sleep(1)
        input(" [>] Press enter to restart pairing ")
        pwm.ChangeDutyCycle(3.1)
        #time.sleep(1)
        print(sensor.enable_color_readings())
        if(sensor.check_for_colored_light(BLUE,45)):
            print(" [.] Reading RGB Color")
            PAIRING = True
            RESTART = False
            
        while PAIRING and not RESTART:
            if(sensor.check_for_colored_light(GREEN, 35)):
                print(" [+] Successfully paired")
                PAIRING = False
                IS_PAIRED = True
                pwm.stop()
            if (sensor.check_for_colored_light(RED, 35)):
                RESTART = True
                break
            #time.sleep(0.25)
            
    return IS_PAIRED

#==================================================================================

#============================  unpairing test  ===============================

def unpairing_sequence():
    sensor = Adsp9960()
    sensor.enable_color_readings()
    #GPIO.setup(13,GPIO.OUT)
    #pwm = GPIO.PWM(13,50)
    #pwm.start(11)
    UNRESTART = False
    UNIS_PAIRED = False
    UNPAIRING = False
    
    while not UNIS_PAIRED:
        if UNRESTART:
            print(" [-] Paired failed, trying again")
            time.sleep(1)
        input(" [>] Press enter to start unpairing ")
        pwm.start(11)
        pwm.ChangeDutyCycle(11)
        time.sleep(1)
        input(" [>] Press enter to restart unpairing ")
        pwm.ChangeDutyCycle(3.1)
        #time.sleep(1)
        print(sensor.enable_color_readings())
        if(sensor.check_for_colored_light(BLUE,45)):
            print(" [.] Reading RGB Color")
            UNPAIRING = True
            UNRESTART = False
            
        while UNPAIRING and not UNRESTART:
            if(sensor.check_for_colored_light(GREEN, 35)):
                print(" [-] Failed, device is still paired")
                UNPAIRING = False
                UNIS_PAIRED = True
                pwm.stop()
            if (sensor.check_for_colored_light(RED, 35)):
                print(" [+] Successfully unpaired")
                UNRESTART = True
                break
            #time.sleep(0.25)
            
    return UNIS_PAIRED
            
#==================================================================================            
#=========================== Ambient light sensor test =============================

def rgb_check(COLOR, TEST_NUMBER,intensity):
    sensor = Adsp9960()
    sensor.enable_color_readings()
    color = ["clear", "red", "green", "blue"]
    RESULT = False
    
    # add here function to close previously activated LED (or just close all of them)
    
    if COLOR == RED:   pass # add code to activate RED   LED (replace "pass" with code or function)
    if COLOR == BLUE:  pass # add code to activate BLUE  LED (replace "pass" with code or function)
    if COLOR == GREEN: pass # add code to activate GREEN LED (replace "pass" with code or function)
    
    for test in range(0,TEST_NUMBER):
        sensor.read_colors()

        if sensor.color_data[COLOR][0]>= intensity:
            print(f'[+] TEST PASSED  {color[COLOR]} LED : {sensor.color_data[COLOR][0]} light units')
            RESULT = True
        else: print(f'[+] TEST FAILED  {color[COLOR]} LED : {sensor.color_data[COLOR][0]} light units')

    return RESULT

#================================================================================== 
#======================== Test sequence: Listen   ============================
def test_Buzzer(DBA_TH=110, time_to_test=1):
    wait_time = 0
    Audible_Alarm_PASS = False
    # activate audible alarm max_level

    while(wait_time<=time_to_test):
        sound_level = check_mic_level()
        if sound_level >= DBA_TH:
            Audible_Alarm_PASS = True
            print(f'\n [+] TEST PASSED  : {sound_level} dBA')
            break;
        time.sleep(1)
        wait_time += 1

    return Audible_Alarm_PASS    


#==================================================================================
#======================== Test sequence: Detection Switches   ============================
# Read the 2 reed switches, if the operator removes the top section while tests are ongoing,
# The test sequence must be canceled.
def Detection_Switches():
    SW1 = GPIO.input(7)
    SW2 = GPIO.input(8)

    result = SW1 and SW2
    
    ENCLOSURE_STATE_FLAG = result

    if not result:
        print(' [-] Test Canceled\n')

    return ENCLOSURE_STATE_FLAG

#==================================================================================

if __name__ == '__main__':
    '''if not is_usb_jlink_connected():
        print('ERROR: Not found USB JLink device')
        exit(1)'''
    PAIRED_FLAG=False
    GLOBAL_RESULTS = 0
    GPIO.setup(13,GPIO.OUT)
    pwm = GPIO.PWM(13,50)
    #pwm.start(3.1)
    time.sleep(1)
    #pwm.ChangeDutyCycle(3.1)
    
    #CSV_STATUS = qr_scan() #Unit ID is scanned (should save data)
 
    is_power_good() #Power of Test PCBA
    if(check_passthrough()):                    GLOBAL_RESULTS + 0b1
    else: 
        print("\n Exit failed Check cables")
        exit(3);
    
  
    jlink_programming() # ask and if need - do with default FW

    while True:
        try:
    #while(Detection_Switches()): ######need to be added back
        # if CSV_STATUS[0] == True:
        
            power_enable() 
            if(check_power_enable()):
                GLOBAL_RESULTS + 0b10
                input("\nReady to program the DUT \nAfter programming is complete, press ENTER to continue.")
                #if(jlink_programming()):            GLOBAL_RESULTS += 0b100
            
            input("\nManufacturing information step, after completing press ENTER to continue.")
            
            if(pairing_sequence()):                 GLOBAL_RESULTS += 0b1000
            
            if(input("\nReady to test RED LED ?   y/n : ") == "y"):
                if(rgb_check(RED,  3, 45)):         GLOBAL_RESULTS += 0b10000
            
            if(input("\nReady to test GREEN LED ? y/n : ") == "y"):
                if(rgb_check(GREEN,3, 35)):         GLOBAL_RESULTS += 0b100000
            
            if(input("\nReady to test BLUE LED ?  y/n : ") == "y"):
                if(rgb_check(BLUE, 3, 45)):         GLOBAL_RESULTS += 0b1000000
            
            if(input("\nReady to test audible alarm highest noise level ? y/n : ") == "y"):
                if(test_Buzzer(time_to_test=6)):    GLOBAL_RESULTS += 0b10000000
                
            if(input("\nReady to unpair? y/n : ") == "y"):
                unpairing_sequence()
            
            print("GLobal results")
            print(GLOBAL_RESULTS)
            
            power_disable()
            print("3 Seconds before power on")
            time.sleep(3)
            '''
            if(CSV_STATUS[0] == True):
                add_csv_log(CSV_STATUS[1], CSV_STATUS[2], CSV_STATUS[3], GLOBAL_RESULTS)
                exit(0)
             '''   
        except KeyboardInterrupt:
            print("Keyboard Interrupt")
            #pwm = GPIO.PWM(13,50)
            pwm.start(3.1)
            time.sleep(1)
            GPIO.output(4,0)
            GPIO.cleanup()
'''
Code sequence: If preflashed
1. Scan QR code (should have Serial number and bluetooth mac)
    Scan will keep the qr code information to counter validate the info on the DUT.
    2.while( switches == True)
        2.1 passthrough
        2.2 Power Enable
        2.3 Pairing
        2.4 Read information -> Compare with scanned info
        2.5 RGB led testing -> automatically activates the Red, Green and Blue leds
        2.6 Audible Alarm -> make the audible alarm buzz >90dBA
        2.7 Unpairing
        2.8 Power off
        2.9 CSV file
            2.9.1 creation of the file if not already done.
            2.9.1 Write in exsisting file with test data.
                Device Serial Number:
                Device BT MAC:
                Date/time:
                Test Data= Final Global_Results
        2.10 Exit script or return to original step.
        
'''