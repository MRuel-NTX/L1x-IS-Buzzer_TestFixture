#!/usr/bin/python3

import csv, json
import os
from time import sleep
import RPi.GPIO as GPIO

dir_path = os.path.dirname(os.path.realpath(__file__))

GPIO_MAP_FNAME = 'rpi_gpio_map.csv'
GPIO_MAP_PATH = os.path.join(dir_path, 'config', GPIO_MAP_FNAME)

gpio_map = {}      # schema: { <gpio_name_str>: {'pin': <int_val>, 'mode': <str_mode>, 'gpio': <int_val>}, }
gpio_rev_map = {}  # schema: { <int_gpio>: <gpio_name_str>, }

class RPI_GPIO:  # class for init GPIOs and set/get values
    def __init__(self):
        print('RPI_GPIO constructor')
        GPIO.setmode(GPIO.BCM)  # BCM enum mode refer to GPIO number of PIN, BOARD enum mode refer to physical PIN number
        GPIO.setwarnings(False) # not show warnings
        GPIO.cleanup()  # clean up all GPIOs before start configuring
        self.init_gpio()

    def init_gpio(self):  # get gpio info from map and do initialization by default
        out_pins_ = [[], []] # by [0] - low out pins, by [1] - high out pins
        in_pins_ = [[], []]  # by [0] - pull down pins, by [1] - pull up pins
        for pin_name in gpio_map:
            pin = gpio_map[pin_name]
            gpio_id = pin['gpio']
            #print(pin_name, ':', pin)  # for debug
            if 'out' in pin['mode']:
                out_pins_[1 if pin['mode'] == 'out:1' else 0].append(gpio_id)  # else - mean: pin['mode'] == 'out:0' or pin['mode'] == 'out'
            elif 'in' in pin['mode']:
                in_pins_[1 if pin['mode'] == 'in:1' else 0].append(gpio_id)  # else - mean: pin['mode'] == 'in:0' or pin['mode'] == 'in'

        if in_pins_[0]: GPIO.setup(in_pins_[0], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        if in_pins_[1]: GPIO.setup(in_pins_[1], GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(out_pins_[0] + out_pins_[1], GPIO.OUT)
        if out_pins_[0]: GPIO.output(out_pins_[0], 0)
        if out_pins_[1]: GPIO.output(out_pins_[1], 1)
        sleep(0.3)

    def set_gpio_value(self, gpio, val):  # setup value for output gpio by name or gpio id, can be apply for output gpio
        ''' gpio - can be a string name of pin from gpio map or gpio int\n
            val - should be int 0 or 1 '''
        pin_name = gpio if (type(gpio) is str) else gpio_rev_map[gpio]
        gpio = gpio_map[gpio]['gpio'] if (type(gpio) is str) else gpio
        print(f'set {val} --> {pin_name} (gpio_{gpio})') # for debug
        GPIO.output(gpio, val)

    def get_gpio_value(self, gpio):  # get value of input gpio by name or gpio id
        ''' gpio - can be a string name of pin from gpio map or gpio int '''
        pin_name = gpio if (type(gpio) is str) else gpio_rev_map[gpio]
        gpio = gpio_map[gpio]['gpio'] if (type(gpio) is str) else gpio
        val = GPIO.input(gpio)
        print(f'get {val} <-- {pin_name} (gpio_{gpio})') # for debug
        return val

    def invert_gpio_value(self, gpio):  # invert value on output pin, and return new value, can be apply for output gpio
        ''' gpio - can be a string name of pin from gpio map or gpio int '''
        pin_name = gpio if (type(gpio) is str) else gpio_rev_map[gpio]
        gpio = gpio_map[gpio]['gpio'] if (type(gpio) is str) else gpio
        old_val = GPIO.input(gpio)
        val = int(not old_val)
        GPIO.output(gpio, val)
        print(f'invert_gpio_value: old {old_val} new {val} for gpio_{gpio} {pin_name}') # for debug
        return val

    def __del__(self):
        #GPIO.cleanup()
        print('RPI_GPIO destructor')

def load_gpio_map(path=GPIO_MAP_PATH):  # read CSV file with gpio map
    print('Try open csv file:', path)
    with open(path) as csvfile:
        # header: pin, mode, name, gpio
        # name - it's a pin name, if name contain (in the beginning  or in the end) hash (#) - it mean what need operate with inverse logic
        # pin  - it's a physical number of pin on RPi
        # gpio - it's a logical number of pin (like a SW model abstraction) 
        # mode - can be - 'in[:0|1]', 'out[:0|1]'
        #     out - without [:0|1] by default as 0 value output
        #     in:0 - with internall pull down
        #     in:1 - with internall pull up
        #     in - without [:0|1] by default as pull down
        # if mode is empty - that mean no need to configure it because not used or it a native interface of RPi
        for row in csv.DictReader(csvfile):
            gpio_map[row['name']] = {'pin': int(row['pin']), 'mode': row['mode'], 'gpio': int(row['gpio'])}
            gpio_rev_map[int(row['gpio'])] = row['name']
        #print(json.dumps(gpio_map, sort_keys=True, indent=4))      # pretty print as JSON
        #print(json.dumps(gpio_rev_map, sort_keys=True, indent=4))  # pretty print as JSON

if __name__ == '__main__':
    print('module RPI_GPIO: selftest')
    load_gpio_map()
    rpi_gpio = RPI_GPIO()  # Configuring GPIOs