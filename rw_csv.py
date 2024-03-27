#!/usr/bin/python3

import os
import csv
import json
import time, os, atexit
import datetime
from datetime import date

dir_path = os.path.dirname(os.path.realpath(__file__))

#========================= Declaration ============================
Default_MAC= "00:00:00:00:00:00"

#data = {'SerialNumber':scanned_qr,'BTMAC':Default_MAC,'TestResult':PASS_FAIL_FLAG}

PASS_FAIL_FLAG = "Fail"

date_today = date.today()
iso_weekday = []
scanflag = True
scanned_isoweek = 0
scanned_qr = []
qr_split = []
create_csv_flag = False
actual_weekday = 0

DUT_FNAME = 'dut_w'+str(actual_weekday)+'.csv' 
DUT_PATH = os.path.join(dir_path,'dut',DUT_FNAME)

data = {'SerialNumber':scanned_qr,'BTMAC':Default_MAC,'TestResult':PASS_FAIL_FLAG}

## Scan QR code, parse data and return DUT info.
#def tempname(scanflag==True):
#def scanning():
while scanflag == True:
    print(data)
    scanned_qr = input('\n'+'Scan DUT QR code'+'\n')
    print('\n'+ scanned_qr)
    if "," in scanned_qr:
        qr_split = scanned_qr.split(',')
        print(qr_split)

    if "AC" in qr_split or scanned_qr:
        scanned_isoweek = scanned_qr[4:6]
            #week2 = qr_split[4:6]
        print('\n'+ scanned_isoweek)
        print(date_today)
        iso_weekday = date_today.isocalendar()
        print(iso_weekday[1])
        print('\n'+scanned_isoweek)
        actual_weekday = iso_weekday[1]

        if actual_weekday == int(scanned_isoweek):
            scanflag = False
            create_csv_flag = True
            print(create_csv_flag)

if create_csv_flag == True:

    DUT_FNAME = 'dut_w'+str(actual_weekday)+'.csv' 
    DUT_PATH = os.path.join(dir_path,'dut',DUT_FNAME)
    # Check if file exists
    if os.path.isfile(DUT_PATH):
        print("path")
        
        # Open the file in append mode
        with open(DUT_PATH, "a", newline="") as file:
            print("path1")
            writer = csv.writer(file)
            
            # Check if the file has data
            if os.stat(DUT_PATH).st_size != 0:
                # Add new data
                print("path2")
                writer.writerow(data)
            else:
                print("File is empty")
                with open(DUT_PATH, mode='w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerows(data)
                    print(f"CSV file '{DUT_PATH}' created successfully.")
    else:
        print("File not found")
        
        



# opening the CSV file  
#with open('Giants.csv', mode ='r')as file:  
      
  # reading the CSV file  
  #csvFile = csv.reader(file)  
    
  # displaying the contents of the CSV file  
  #for lines in csvFile:  
        #print(lines) 