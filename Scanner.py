#!/usr/bin/python3

import os
import csv
import json
import time, os, atexit
import datetime
from datetime import date

scanflag = True
scanned_qr = []
qr_split = []

## Scan QR code, parse data and return DUT info.
#def tempname(scanflag==True):
#def scanning():
while scanflag == True:
    scanned_qr = input('\n'+'Scan DUT QR code')
    print('\n'+ scanned_qr)
    if "," in scanned_qr:
        qr_split = scanned_qr.split(',')
        print(qr_split)
    if "AC" in qr_split or scanned_qr:
        isoweek = scanned_qr[4:6]
            #week2 = qr_split[4:6]
        print('\n'+ isoweek)
            #print('\n'+ week2)
        scanflag = False
    print(scanflag)
#return isoweek

#if __name__ == '__main__':
#    print('module scan')
#    scanflag = True
#    scanned_qr = []
#    qr_split = []
#    scanning()