#!/usr/bin/python3

import os
import csv
from datetime import date

def qr_code_csv(DUT_SN,DUT_MAC,PASS_FAIL_FLAG):
    #DUT_MAC= "00:00:00:00:00:00"
    #PASS_FAIL_FLAG = ""
    dir_path = os.path.dirname(os.path.realpath(__file__))
    scanflag = True
    actual_weekday = 0
    #DUT_SN = ""
    CSV_FLAG = 'False'

    while scanflag:
        scanned_qr = input('\n'+'Scan DUT QR code'+'\n')
        print('\n'+ scanned_qr)
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
                header = {'SerialNumber','BTMAC','TestResult'}
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
                        print(f"Data written to '{DUT_PATH}'.")
                else:
                    with open(DUT_PATH, 'w', newline='', encoding='utf-8') as file:
                        writer = csv.DictWriter(file, fieldnames=data.keys())
                        writer.writeheader(header)
                        writer.writerow(data)
                        CSV_FLAG = 'True'
                        print(f"CSV file '{DUT_PATH}' created and data written.")
    return CSV_FLAG