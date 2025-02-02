import os
from machine import Pin, SPI
from st7789_170x320 import *
from gc import collect
from time import sleep

def display_image(filename, orient=0):
    ''' orient = 0, 2 -> paysage
                   4, 6 -> portrait '''
    with open(filename + '.raw', 'rb') as fd:
        fd.readinto(buf)
        if orient // 4:
            st.blit_buffer(buf, 0, 0, 320, 170)
        else:
            st.blit_buffer(buf, 0, 0, 170, 320)

os.chdir('/ST7789 170x320')
spi = SPI(1, baudrate=40000000, sck=Pin(4), mosi=Pin(3), miso=None)

reset = Pin(2, Pin.OUT)
cs    = Pin(0, Pin.OUT)
dc    = Pin(1, Pin.OUT)
bl    = Pin(5, Pin.OUT)

buf = bytearray(170*320*2)
st = ST7789(spi, cs, dc, reset, bl, disp_mode=0)

for name, mode in (('paysage', 4), ('cheval', 2), ('bateaux', 4), ('amanite', 2)):
    st.change_mode(mode)
    display_image(name, orient=mode)
    sleep(4)

del buf
collect