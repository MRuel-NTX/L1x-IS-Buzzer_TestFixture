from smbus2 import SMBus

FUNC_CALL_ERR = -1
I2C_FAILURE = -2

CLEAR = 0
RED   = 1
GREEN = 2
BLUE  = 3
APDS9960_EN_REG   = 0x80
APDS9960_GAIN_REG = 0x8F

class Adsp9960:
    def __init__(self, i2c=1):
        self.i2c = SMBus(i2c)
        self.addr = 0x39
        self.read_reg = [0x94, 0x96, 0x98, 0x9A]
        self.color_data = [[], [], [], []]
        
    def enable_color_readings(self):
        try:
            self.i2c.write_byte_data(self.addr, APDS9960_EN_REG, 0x01)  # pwr on
            self.i2c.write_byte_data(self.addr, APDS9960_EN_REG, 0x03)  # enable
            return True
        except Exception:
            return I2C_FAILURE 

    def read_ambient_light_register(self, color):
        if CLEAR <= color <= BLUE:
            try:
                data = self.i2c.read_i2c_block_data(self.addr, self.read_reg[color], 2)
                self.color_data[color] = data
                return data
            except Exception:
                return I2C_FAILURE 
        else:
            return FUNC_CALL_ERR
    
    def read_colors(self):
        try:
            for color in [CLEAR, RED, GREEN, BLUE]:
                self.color_data[color] = self.read_ambient_light_register(color)
            return self.color_data
        except Exception:
            return I2C_FAILURE
        
    def set_gain(self, gain):
        if 0 <= gain <= 3:
            try:
                self.i2c.write_byte_data(self.addr, APDS9960_GAIN_REG, gain)
                return True
            except Exception:
                return I2C_FAILURE
        else:
            return FUNC_CALL_ERR

    def get_stored_color_data(self, color):
        if CLEAR <= color <= BLUE:
            return self.color_data[color]
        else:
            return FUNC_CALL_ERR
    
    def check_for_colored_light(self, color, intensity):
        self.read_ambient_light_register(color)
        return self.color_data[color][0] >= intensity
    
    def read_expected_color(self, color, expected_intensity):
        self.read_ambient_light_register(color)
        actual_intensity = self.get_stored_color_data(color)[0]
        return actual_intensity >= expected_intensity