#!/usr/bin/python3

import os
import datetime
import subprocess
from pathlib import Path

HEADER_WIDTH = 100

dir_path = os.path.dirname(os.path.realpath(__file__))

FW_FNAME = 'mcuboot_app_merged_1.6.23+0.hex'  # can move this in the config file
FW_PATH = os.path.join(dir_path, 'jlink_fw', FW_FNAME)  # the same - move hardcode path to config file

JLINK_SCRIPT_FNAME = '.'.join([Path(FW_FNAME).stem, 'jlink'])
JLINK_SCPIRT_PATH = os.path.join(dir_path, 'jlink_fw', JLINK_SCRIPT_FNAME)

JLINK_TEMPLATE_SCRIPT_FNAME = 'template_script.jlink'
JLINK_TEMPLATE_SCPIRT_PATH = os.path.join(dir_path, 'jlink_fw', JLINK_TEMPLATE_SCRIPT_FNAME)

#==================================================================================
# create required file structure before start
# make 'log' folder in the currect working folder
LOG_PATH = os.path.join(dir_path, 'log')
if not os.path.exists(LOG_PATH):
    os.makedirs(LOG_PATH)

# create jlink script from template if not exist yet for specified FW
FW_PATH_REPLACE_MARKER = 'FW_PATH'
if not os.path.exists(JLINK_SCPIRT_PATH):
    with open(JLINK_TEMPLATE_SCPIRT_PATH, 'r') as jlink_script_template:
        script = jlink_script_template.readlines()
        with open(JLINK_SCPIRT_PATH, 'w') as jlink_script:
            for line in script:
                if FW_PATH_REPLACE_MARKER in line:
                    lkw = line.strip().split()
                    lkw[1] = FW_PATH   # it because line should be as: 'loadfile FW_PATH'
                    line = ' '.join(lkw) + '\n'
                jlink_script.write(line)

# check on presence USB JLink programmator
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

#====================== Test sequence: JLink programming ==========================
def jlink_programming(script_path=JLINK_SCPIRT_PATH):  # run script by external segger command tool for jlink programming
    ''' script_path - it's a string with a full path on jlink script\n
        jlink script consist all required parameters: device, frequency, name of srec file and programming address;\n
        and shoud run in a segger command tool '''
    print('\n' + f' JLINK PROGRAMMING UUT '.center(HEADER_WIDTH, '='))
    if not os.path.isfile(script_path):
        print(f'JLink script {script_path} not found')
        return False

    dt = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    LOG_FNAME = os.path.join(LOG_PATH, f'JLink_UUT_{dt}.log')
    print(f'Run jlink scrpt:\n  {script_path}')
    # run JLinkExe program without GUI and don't output log of execution but save it in the file
    # JLink tool feature: '-Log', LOG_FNAME; it produce a big detailed log
    response = subprocess.run(['JLinkExe', '-NoGui', '1', '-CommandFile', script_path], shell=False, capture_output=True)

    with open(LOG_FNAME, 'w') as jlog:  # save jlink output to log file
        jlog.write(response.stdout.decode('utf-8'))

    res = True if response.returncode == 0 else False
    print(f'JLink programming for UUT is {"OK" if res else "FAILED"}')
    print(f'For details see log in the file:\n  {LOG_FNAME}')
    print('\n' + f''.center(HEADER_WIDTH, '='))
    return res

#==================================================================================

if __name__ == '__main__':
    print('Test jlink module')
    if is_usb_jlink_connected():
        jlink_programming()