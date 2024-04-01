
# command = 'mosquitto_pub -t b1x/events/ble/a3x-manager/request -m "{\\"getConfig\\": { } }"'
# "mosquitto_pub -t b1x/events/ble/a3x-manager/request -m '{ \"leds\": {\"intensity\":0,\"onLengthMs\":100,\"blinkingPeriodMs\":900,\"redIntensity\":0,\"greenIntensity\":0,\"blueIntensity\":0} }'"
# "mosquitto_pub -t b1x/events/ble/a3x-manager/request -m '{ \"pairingRequest\": { } }'"

import paramiko
import RPi.GPIO as GPIO
from datetime import date
from pathlib import Path
from servo import Servo 


ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.WarningPolicy)

command2 = "mosquitto_pub -t b1x/events/ble/a3x-manager/request -m '{ \"pairingRequest\": { } }'"
command = "mosquitto_pub -t b1x/events/ble/a3x-manager/request -m '{ \"leds\": {\"intensity\":0,\"onLengthMs\":100,\"blinkingPeriodMs\":900,\"redIntensity\":0,\"greenIntensity\":0,\"blueIntensity\":0} }'"

try:
    ssh.connect('169.254.10.10', username='root', password='')
    #stdin, stdout, stderr = ssh.exec_command('mkdir ./test/test1')  # replace '' with your command
    #print(stdout.read().decode())

    # Send a status update request
    stdin, stdout, stderr = ssh.exec_command(command2)

    # Wait for the command to complete
    exit_status = stdout.channel.recv_exit_status()

    # If the command completed successfully, read the output
    if exit_status == 0:
        response = stdout.read().decode()
        print("Response:", response)
    else:
        print("Command failed with exit status:", exit_status)

    # Close the SSH connection
    ssh.close()

except paramiko.AuthenticationException:
    print("Authentication failed, please verify your credentials.")
except paramiko.SSHException as sshException:
    print(f"Unable to establish SSH connection: {sshException}")

except Exception as e:
    print(e)

'''
import paramiko
import time

# Create a new SSH client
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# Connect to the SoM
ssh.connect('169.254.10.10', username='root', password='your_password')

# Wait until powergood function flag is True
while not powergood_function():
    time.sleep(1)  # wait for 1 second

# Send a command to start programming the device
stdin, stdout, stderr = ssh.exec_command('')

# Wait for the command to complete
stdout.channel.recv_exit_status()

# Once programming is done, send a command to get the serial number
stdin, stdout, stderr = ssh.exec_command('')

# Wait for the command to complete and get the output
exit_status = stdout.channel.recv_exit_status()
if exit_status == 0:
    serial_number = stdout.read().decode()

# Send a command to get the Bluetooth MAC
stdin, stdout, stderr = ssh.exec_command('')

# Wait for the command to complete and get the output
exit_status = stdout.channel.recv_exit_status()

if exit_status == 0:
    bluetooth_mac = stdout.read().decode()

# Close the SSH connection when done
ssh.close()
'''