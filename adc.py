#!/usr/bin/python3

import os
import csv
import json
import ads1219

dir_path = os.path.dirname(os.path.realpath(__file__))

ADC_CONF_FNAME = 'adc_config.csv'
ADC_CONF_PATH = os.path.join(dir_path, 'config', ADC_CONF_FNAME)

ADC_AINs = 4
POWER_GOOD_ADC = 'POWER_GOOD'

adc_map = {}  # {'<adc_name>': {'i2c_addr': <int_hex_val>, 'vref': <float_val>, 'div_coef': [<float_val>, ], 'deviation_percent': <int_val>, 'ain_input_v': ['str_float_val', ] }, }
adc_addr = [] # list of ADCs i2c addresses

def load_adc_conf(path=ADC_CONF_PATH):  # load ADCs info from CSV config file
    print('Try open config file:', path)
    with open(path) as config:
        # header: #name, i2c_addr, vref, ain0_input_v, div0_coef, ain1_input_v, div1_coef, ain2_input_v, div2_coef, ain3_input_v, div3_coef, common_div_coef, deviation_percent
        # parse values 'ain0_input_v, ain1_input_v, ain2_input_v, ain3_input_v' and push it in a list by index, read as string value because can be specified as range of values - "a.b_c.d" 
        # parse values 'div0_coef, div1_coef, div2_coef, div3_coef' and push it in a list by index
        for row in csv.DictReader(config):
            common_dif_coef = float(row['common_div_coef'].strip()) if row['common_div_coef'].strip() else 1  # if common_div_coef not specified - get as 1
            adc_addr.append(int(row['i2c_addr'].strip(), 16))
            adc_map[row['name'].strip()] = {'i2c_addr'         :  int  (row['i2c_addr'         ].strip(), 16),
                                            'deviation_percent':  int  (row['deviation_percent'].strip()),
                                            'vref'             :  float(row['vref'             ].strip()),
                                            'ain_input_v'      : [     (row[f'ain{id}_input_v' ].strip()) if row[f'ain{id}_input_v'].strip() else None            for id in range(ADC_AINs)],
                                            'div_coef'         : [float(row[f'div{id}_coef'    ].strip()) if row[f'div{id}_coef'   ].strip() else common_dif_coef for id in range(ADC_AINs)]}
        #print(json.dumps(adc_map, sort_keys=True, indent=2))  # for debug, pretty print as JSON

def check_adc_voltage(name, ain_id=None):
    ''' name - a string value of ADC name\n
        ain_id - int value from 0 to 3; if it not specified - will check voltage for all active AINs\n
    Return: boolean result '''
    if (ain_id != None) and (not ain_id in range(ADC_AINs)):
        print(f'ERROR: Specified not a correct AIN id:{ain_id}')
        return False

    adc_info = adc_map[name]
    ain_vl = adc_info['ain_input_v']
    vref   = adc_info['vref']
    dev_percent = adc_info['deviation_percent']

    print('ADC:', name)
    adc = ads1219.ADS1219(adc_info['i2c_addr'])
    adc.set_vref(ads1219.VREF_EXTERNAL, vref)

    res = True
    ain_lut = (ads1219.MUX_AIN_0, ads1219.MUX_AIN_1, ads1219.MUX_AIN_2, ads1219.MUX_AIN_3)

    for id in range(ADC_AINs):
        if (ain_id != None) and (ain_id != id): continue
        ain_val = ain_vl[id]
        div_coef = adc_info['div_coef'][id]

        if not ain_val: continue  # value is empty string or None
        
        exp_val = low_val = high_val = None
        if '_' in ain_val:  # it mean ain expected value consist a range of low_high values
            low, high = map(float, ain_val.split('_'))
            low_val  = round((low  / div_coef) * (1 - dev_percent/100), 3)
            high_val = round((high / div_coef) * (1 + dev_percent/100), 3)
            if (high_val > vref): high_val = vref
            exp_val = f'{low_val}<-->{high_val}'
        else:
            ain_val = float(ain_val)
            # get value from ADS1219 and do comparison with permissible deviations
            exp_val  = round(ain_val / div_coef, 3)
            low_val  = round(exp_val * (1 - dev_percent/100), 3)
            high_val = round(exp_val * (1 + dev_percent/100), 3)
            if (high_val > vref): high_val = vref

        actual_val = round(adc.convert_to_V(adc.read_single(ain_lut[id])), 3)

        if (low_val <= actual_val) and (actual_val <= high_val):
            print('OK:', end='')
        else:
            print('FAILED:', end='')
            res = False
        print(f'\tAIN{id}: exp_val [{exp_val}], low_val [{low_val}], high_val [{high_val}], actual_val [{actual_val}]')
        if ain_id != None: break  # loop optimization - exit from loop because already check value for specified AIN
    return res

def get_adc_voltage(name, ain_id=None):
    ''' name - a string value of ADC name\n
        ain_id - int value from 0 to 3; if it not specified - will check voltage for all active AINs\n
    Return: list of value(s) '''
    if (ain_id != None) and (not ain_id in range(ADC_AINs)):
        print(f'ERROR: Specified not a correct AIN id:{ain_id}')
        return False

    adc_info = adc_map[name]
    adc = ads1219.ADS1219(adc_info['i2c_addr'])
    adc.set_vref(ads1219.VREF_EXTERNAL, adc_info['vref'])

    res = []
    ain_lut = (ads1219.MUX_AIN_0, ads1219.MUX_AIN_1, ads1219.MUX_AIN_2, ads1219.MUX_AIN_3)

    for id in range(ADC_AINs):
        if (ain_id != None) and (ain_id != id): continue

        actual_val = round(adc.convert_to_V(adc.read_single(ain_lut[id])), 3)
        res.append(actual_val)
        if ain_id != None: break  # loop optimization - exit from loop because already get value for specified AIN

    print(f'ADC: [{name}], AINs voltage: {res}')
    return res

def check_availability(i2c_addr=None):  # main goal to check if ADC is present on a i2c bus
    '''' i2c_addr - list of int hex\n
    by default without argument will use internal adc_addr list\n
    Retutn: boolean result '''
    res = True
    if not i2c_addr: i2c_addr = adc_addr
    for addr in i2c_addr:
        try:
            print(f'Try to get access for ADC [{hex(addr)}]')
            with ads1219.ADS1219(addr): print('Access is OK')
        except OSError as ex:
            res = False
            print(f'Access is FAILED: {ex}')
    return res


if __name__ == '__main__':
    print('adc module selftest')
    load_adc_conf()
    if check_availability():
        print('OK: ADCs in the system and power ON')
        check_adc_voltage(POWER_GOOD_ADC)