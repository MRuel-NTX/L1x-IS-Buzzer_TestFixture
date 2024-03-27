#!/usr/bin/python3

import csv, json
import os
from time import sleep
import RPi.GPIO as GPIO

'''
basic usage (for BUZZER) : 
                actuator = Servo(pin=13)               # initialise
                actuator.set_duty_cycle_range(2.5, 13) # set the Pulsewidth range as % (2.5% to 13% of the period)
                actuator.set_angle(0)                  # choose positions to set
                actuator.set_angle(180)                # repeat as necessary
                
Values here should be alright with our choice of component
'''

class Servo():
    def __init__(self, pin, frequency=50, max_angle=180):
        self.max_angle = max_angle
        self.servo_pwm = GPIO.PWM(pin, frequency)   # PWM initialisation 
        self.servo_pwm.start(0)                     # duty cycle started at 0% for no movement
    
    def set_duty_cycle_range(self, min_duty, max_duty):
        ''' These values are used to calculate pulsewidths later on
            - min_duty : minimum duty cycle represented as % of the period (just as a float)
            - max_duty : maximum duty cycle represented as % of the period (just as a float)
            Ex : freq = 50 -> P = 20ms
                 if minimum dutycycle is 1ms so min_duty would be 5  (%)
                 if maximum dutycycle is 5ms so max_duty would be 25 (%)  
            Ex values are not real component values***
        '''
        self.min_duty = (min_duty)
        self.max_duty = (max_duty)
        self.duty_range = (max_duty-min_duty)
    
    def set_duty_cycle(self, duty):
        if(duty >= self.min_duty and duty<= self.max_duty):
            self.servo_pwm.ChangeDutyCycle(duty)
    
    def set_angle(self,angle):
        if type(angle) is float and angle>=0 and angle<=self.max_angle:
            duty_cycle =(((angle/self.max_angle)*self.duty_range)+self.min_duty)
            self.set_duty_cycle(duty_cycle)