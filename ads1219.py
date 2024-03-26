#!/usr/bin/python3

from time import sleep
from smbus2 import SMBus, i2c_msg

def get_var_name(var, map=None):  # service function for getting constant variable name as string
    if map:
        try:
            return map[var]
        except:
            print('Not found var in the local map')
    for var_name in globals():
        if eval(var_name) == var:
            return var_name
    return None

CMD_POWERDOWN   = 0x02
CMD_RESET       = 0x06
CMD_START_SYNC  = 0x08
CMD_RDATA       = 0x10
CMD_RREG_CFG    = 0x20
CMD_RREG_STATUS = 0x24
CMD_WREG_CFG    = 0x40

MUX_MASK        = 0x1F
MUX_DIF_0_1     = 0x00  # Differential P = AIN0, N = AIN1 (default)
MUX_DIF_2_3     = 0x20  # Differential P = AIN2, N = AIN3
MUX_DIF_1_2     = 0x40  # Differential P = AIN1, N = AIN2
MUX_AIN_0       = 0x60
MUX_AIN_1       = 0x80
MUX_AIN_2       = 0xa0
MUX_AIN_3       = 0xc0
MUX_SHORTED     = 0xe0  # Mid-supply   P = AVDD/2, N = AVDD/2

GAIN_MASK       = 0xEF
GAIN_1X         = 0x00  # Gain = 1 (default)
GAIN_4X         = 0x10

DATA_RATE_MASK  = 0xF3
DATA_RATE_20    = 0x00  # Data rate = 20 SPS (default)
DATA_RATE_90    = 0x04
DATA_RATE_330   = 0x08
DATA_RATE_1000  = 0x0c

MODE_MASK       = 0xFD
MODE_SINGLESHOT = 0x00  # Single-shot conversion mode (default)
MODE_CONTINUOUS = 0x02

VREF_MASK       = 0xFE
VREF_INTERNAL   = 0x00  # Internal 2.048V reference (default)
VREF_EXTERNAL   = 0x01

VREF_INTERNAL_V     = 2.048     # Internal reference voltage = 2.048 V
POSITIVE_CODE_RANGE = 0x7FFFFF  # 23 bits of positive range

cmd_names_map = { CMD_POWERDOWN: 'CMD_POWERDOWN',
                  CMD_RESET: 'CMD_RESET',
                  CMD_START_SYNC: 'CMD_START_SYNC',
                  CMD_RDATA: 'CMD_RDATA',
                  CMD_RREG_CFG: 'CMD_RREG_CFG',
                  CMD_RREG_STATUS: 'CMD_RREG_STATUS',
                  CMD_WREG_CFG: 'CMD_WREG_CFG' }

mux_names_map = { MUX_MASK: 'MUX_MASK',
                  MUX_DIF_0_1: 'MUX_DIF_0_1',
                  MUX_DIF_2_3: 'MUX_DIF_2_3',
                  MUX_DIF_1_2: 'MUX_DIF_1_2',
                  MUX_AIN_0: 'MUX_AIN_0',
                  MUX_AIN_1: 'MUX_AIN_1',
                  MUX_AIN_2: 'MUX_AIN_2',
                  MUX_AIN_3: 'MUX_AIN_3',
                  MUX_SHORTED: 'MUX_SHORTED' }

datarate_names_map = { DATA_RATE_20: 'DATA_RATE_20',
                       DATA_RATE_90: 'DATA_RATE_90',
                       DATA_RATE_330: 'DATA_RATE_330',
                       DATA_RATE_1000: 'DATA_RATE_1000' }

gain_names_map = { GAIN_1X: 'GAIN_1X', GAIN_4X: 'GAIN_4X' }
mode_names_map = { MODE_SINGLESHOT: 'MODE_SINGLESHOT', MODE_CONTINUOUS: 'MODE_CONTINUOUS' }
vref_names_map = { VREF_INTERNAL: 'VREF_INTERNAL', VREF_EXTERNAL: 'VREF_EXTERNAL' }

DEBUG_MODE = False

class ADS1219:
    def __init__(self, addr=0x40, bus_num=1):  # Constructor
        ''' bus_num:     int, I2C bus_num, for raspberry with bus_num 2 and 3 please set to bus_num=1
            addr   :  hex, I2C adress of the chip. Default is 0x40 '''
        print(f'ADS1219({hex(addr)}) constructor')
        self.i2c_addr = addr
        self.bus = SMBus(bus_num, True)
        self.reset()

    def write_cmd(self, cmd):  # Send command data: hex value
        if DEBUG_MODE: print(f'Write cmd: {hex(cmd)}  name: {get_var_name(cmd, cmd_names_map)}')  # for debug
        self.bus.write_byte(self.i2c_addr, cmd)

    def start(self):  # Starting the work of taking results
        if DEBUG_MODE: print('Start SYNC')  # for debug
        self.write_cmd(CMD_START_SYNC)

    def reset(self):  # Reset chip
        if DEBUG_MODE: print('Reset')  # for debug
        self.config = 0x00  # all values set as default
        self.gain = 1
        self.V_ref = VREF_INTERNAL_V
        self.write_cmd(CMD_RESET)

    def power_off(self):  # Power off the chip
        if DEBUG_MODE: print('Power off')  # for debug
        self.write_cmd(CMD_POWERDOWN)

    def read_register(self, reg, size):  # Read data from registers
        ''' reg: hex, register to write
            size: int, size of data
        Return: list: data read '''
        if DEBUG_MODE: print(f'Read register: {hex(reg)}  name: {get_var_name(reg, cmd_names_map)}, size of readback data: {size} byte{"s" if size>1 else ""}')  # for debug
        write = i2c_msg.write(self.i2c_addr, [reg])
        read  = i2c_msg.read(self.i2c_addr, size)
        self.bus.i2c_rdwr(write, read)
        return list(read)

    def send_config(self, val=None):  # Send config to the chip
        ''' val - int hex 1 byte value.\n
        Note: if use this function with a custom value - need to be confident what it was not logicaly affect V_ref and gain values.\n
        In case if it touch this values - it needs to setup manually new correct values for (gain and V_ref). '''
        if val: self.config = val
        if DEBUG_MODE: print(f'Send config: {hex(self.config)}  reg name: {get_var_name(CMD_WREG_CFG, cmd_names_map)}')  # for debug
        self.bus.write_byte_data(self.i2c_addr, CMD_WREG_CFG, self.config)

    def set_gain(self, gain=GAIN_1X):  # Define the gain
        ''' gain: int, value of the gain: GAIN_1X or GAIN_4X (default: GAIN_1X) '''
        if gain in (GAIN_1X, GAIN_4X):
            self.config = (self.config & GAIN_MASK) | gain
            self.gain = 1 if gain == GAIN_1X else 4
        else: raise ValueError("'gain' can only be either GAIN_1X or GAIN_4X")
        if DEBUG_MODE: print('Set gain:', get_var_name(gain, gain_names_map))  # for debug
        self.send_config()

    def set_data_rate(self, datarate=DATA_RATE_20):  # Define the datarate
        ''' datarate: int, value of the datarate: DATA_RATE_<20|90|330|1000> (default: 20)
            size:     int, size of data '''
        if datarate in (DATA_RATE_20, DATA_RATE_90, DATA_RATE_330, DATA_RATE_1000): self.config = (self.config & DATA_RATE_MASK) | datarate
        else: raise ValueError("'datarate' can only be either DATA_RATE_20, DATA_RATE_90, DATA_RATE_330 or DATA_RATE_1000")
        if DEBUG_MODE: print('Set datarate:', get_var_name(datarate, datarate_names_map))  # for debug
        self.send_config()

    def set_mode(self, mode=MODE_SINGLESHOT):  # Configure the chip in Single Shot or Continuous mode
        ''' mode - int value MODE_SINGLESHOT or MODE_CONTINUOUS, (MODE_SINGLESHOT by default) '''
        if mode in (MODE_SINGLESHOT, MODE_CONTINUOUS): self.config = (self.config & MODE_MASK) | mode
        else: raise ValueError("'mode' can only be either MODE_SINGLESHOT or MODE_CONTINUOUS")
        if DEBUG_MODE: print('Set mode:', get_var_name(mode, mode_names_map))  # for debug
        self.send_config()

    def set_vref(self, ref, value=VREF_INTERNAL_V):  # Configure the chip with an internal or external reference
        ''' ref: int, VREF_INTERNAL or VREF_EXTERNAL
        value: float, value of the external reference; for VREF_INTERNAL value will be ignored '''
        self.V_ref = value if ref == VREF_EXTERNAL else VREF_INTERNAL_V
        self.config = (self.config & VREF_MASK) | (VREF_EXTERNAL if ref == VREF_EXTERNAL else VREF_INTERNAL)
        if DEBUG_MODE: print(f'Set type vref: {get_var_name(ref, vref_names_map)}  Voltage: {self.V_ref}')  # for debug
        self.send_config()

    def read_config(self):  # Get chip config
        if DEBUG_MODE: print(f'Read config from: {hex(CMD_RREG_CFG)}  name: {get_var_name(CMD_RREG_CFG, cmd_names_map)}')  # for debug
        data = self.read_register(CMD_RREG_CFG, 1)     # write CMD_RREG_CFG and read 1 byte response
        if DEBUG_MODE: print('Config:', hex(data[0]))  # for debug
        return data[0]

    def read_status(self):  # Get chip status
        if DEBUG_MODE: print(f'Read status from: {hex(CMD_RREG_STATUS)}  name: {get_var_name(CMD_RREG_STATUS, cmd_names_map)}')  # for debug
        data = self.read_register(CMD_RREG_STATUS, 1)  # write CMD_RREG_STATUS and read 1 byte response
        if DEBUG_MODE: print('Status:', hex(data[0]))  # for debug
        return data[0]

    def read_data(self):  # Get the result data from the chip
        buf = self.read_register(CMD_RDATA, 3)
        if DEBUG_MODE: print('Read data:', hex(buf[0]), hex(buf[1]), hex(buf[2]))  # for debug
        value = (buf[0] << 16) | (buf[1] << 8) | (buf[2])
        if value >= 0x800000: value -= 0x1000000
        return value

    def is_ready(self):  # Software function to get the moment when the data is available
        value = self.read_status()
        return ((value & 0x80) == 0x80)

    def wait_result(self):  # Blocking function to wait data
        if DEBUG_MODE: print('Wait result')  # for debug
        while not self.is_ready():
            sleep(0.0001)

    def read_single(self, channel):  # Read a value from a specific channel
        ''' channel: int, channel number: MUX_AIN_0, MUX_AIN_1, MUX_AIN_2 or MUX_AIN_3 '''
        if channel in (MUX_AIN_0, MUX_AIN_1, MUX_AIN_2, MUX_AIN_3): self.config = (self.config & MUX_MASK) | channel
        else: raise ValueError("'channel' can only be either MUX_AIN_0, MUX_AIN_1, MUX_AIN_2 or MUX_AIN_3")
        if DEBUG_MODE: print('Read single:', get_var_name(channel, mux_names_map))  # for debug
        #print('Read old config:', hex(self.read_config()))  # for debug
        self.send_config()
        #print('Read new config:', hex(self.read_config()))  # for debug
        self.start()
        self.wait_result()
        return self.read_data()

    def read_diff(self, dif=MUX_DIF_0_1):  # Read a value between 0_1, 1_2 or 2_3 channels; and shorted mode
        ''' diff - int value should be MUX_SHORTED, MUX_DIF_0_1 (by default), MUX_DIF_1_2 or MUX_DIF_2_3 '''
        # shorted mode - set the chip to get an offset to calibrate; refer to 8.3.7 in the datasheet https://www.ti.com/lit/ds/sbas924a/sbas924a.pdf
        if dif in (MUX_SHORTED, MUX_DIF_0_1, MUX_DIF_1_2, MUX_DIF_2_3): self.config = (self.config & MUX_MASK) | dif
        else: raise ValueError("'between' can only be either MUX_SHORTED, MUX_DIF_0_1, MUX_DIF_1_2 or MUX_DIF_2_3")
        if DEBUG_MODE: print('Read diff:', get_var_name(dif, mux_names_map))  # for debug
        self.send_config()
        self.start()
        self.wait_result()
        return self.read_data()

    def convert_to_V(self, value):  # Function to convert the value in Volt using Gain and Vref
        ''' value: float, value to convert
        Return: float, value in V '''
        return (self.V_ref * value) / (self.gain * POSITIVE_CODE_RANGE)
#===============================================================================================

    def __enter__(self):  # __enter__ and __exit__ functions use for possibility working in the context 'with' statement
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        self.bus.close()
    def __del__(self):  # Destructor
        print(f'ADS1219({hex(self.i2c_addr)}) destructor')
        self.bus.close()


if __name__ == '__main__':
    print('ADS1219 lib')
    print('module selftest')
    ads = ADS1219(0x45)
    ads.set_vref(VREF_EXTERNAL, 5.0)
    ads.set_data_rate(DATA_RATE_20)
    ads.set_gain(GAIN_1X)
    ads.set_mode(MODE_SINGLESHOT)

    print(f'AIN0: {round(ads.convert_to_V(ads.read_single(MUX_AIN_0)), 3)} V')
    print(f'AIN1: {round(ads.convert_to_V(ads.read_single(MUX_AIN_1)), 3)} V')
    print(f'AIN2: {round(ads.convert_to_V(ads.read_single(MUX_AIN_2)), 3)} V')
    print(f'AIN3: {round(ads.convert_to_V(ads.read_single(MUX_AIN_3)), 3)} V')
    print(f'SHORTED: {round(ads.convert_to_V(ads.read_diff(MUX_SHORTED)), 3)} V')
    print(f'DIF_0_1: {round(ads.convert_to_V(ads.read_diff(MUX_DIF_0_1)), 3)} V')
    print(f'DIF_1_2: {round(ads.convert_to_V(ads.read_diff(MUX_DIF_1_2)), 3)} V')
    print(f'DIF_2_3: {round(ads.convert_to_V(ads.read_diff(MUX_DIF_2_3)), 3)} V')
#################################################################################################