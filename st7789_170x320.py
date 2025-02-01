##############################################################
#
#    Driver spécifique pour le ST7789 170x320 1.9" 
#    http://www.lcdwiki.com/1.9inch_IPS_Module
#
#    Adapté de st7789py.py de Russ Hughes
#    voir https://github.com/russhughes/st7789py_mpy
#
##############################################################

from time import sleep_ms
import gc
from struct import pack, unpack
from math import atan2, pi

# ST7789 commands
_ST7789_SWRESET = b"\x01"
_ST7789_SLPIN   = b"\x10"
_ST7789_SLPOUT  = b"\x11"
_ST7789_NORON   = b"\x13"
_ST7789_INVOFF  = b"\x20"
_ST7789_INVON   = b"\x21"
_ST7789_DISPOFF = b"\x28"
_ST7789_DISPON  = b"\x29"
_ST7789_CASET   = b"\x2a"
_ST7789_RASET   = b"\x2b"
_ST7789_RAMWR   = b"\x2c"
_ST7789_VSCRDEF = b"\x33"
_ST7789_COLMOD  = b"\x3a"
_ST7789_MADCTL  = b"\x36"
_ST7789_VSCSAD  = b"\x37"
_ST7789_RAMCTL  = b"\xb0"
# User orientation constants
MODE = (0x00, 0x40, 0xC0, 0x80,     # landscape
        0x60, 0xE0, 0xA0, 0x20)     # portrait
# Color definitions (RGB565)
BLACK   = b'\x00\x00'
BLUE    = b'\x00\x08'
RED     = b'\xF8\x00'
GREEN   = b'\x07\xE0'
CYAN    = b'\x07\xFF'
MAGENTA = b'\xF8\x1F'
YELLOW  = b'\xFF\xE0'
ORANGE  = b'\xFC\x00'
WHITE   = b'\xFF\xFF'
#
_BUFFER_SIZE = const(256)

_BIT7 = const(0x80)
_BIT6 = const(0x40)
_BIT5 = const(0x20)
_BIT4 = const(0x10)
_BIT3 = const(0x08)
_BIT2 = const(0x04)
_BIT1 = const(0x02)
_BIT0 = const(0x01)
#
class ST7789:

    def __init__(self, spi, cs, dc, rst, bl, height=240, width=240, disp_mode=4):
        
        if not 0 <= disp_mode <= 7:
            raise ValueError("Invalid display mode:", disp_mode)
        self._spi = spi
        self._rst = rst
        self._dc = dc
        self._cs = cs
        self._bl = bl
        self.mode = disp_mode
        gc.collect()
        self.buf = bytearray(_BUFFER_SIZE)
        self.turn_on()
        self._init()
        self.clear()

    def _hwreset(self):
        ''' hardware reset '''
        self._dc(0)
        self._rst(1)
        sleep_ms(1)
        self._rst(0)
        sleep_ms(1)
        self._rst(1)
        sleep_ms(1)

    def _wcmd(self, buf):
        ''' Write a command, a bytes instance (1 byte) '''
        self._dc(0)
        self._cs(0)
        self._spi.write(buf)
        self._cs(1)

    def _wcd(self, c, d):
        ''' Write command c (1 byte) followed by data d (bytes) '''
        self._dc(0)
        self._cs(0)
        self._spi.write(c)
        self._cs(1)
        self._dc(1)
        self._cs(0)
        self._spi.write(d)
        self._cs(1)
    
    def _init(self):
        ''' Initialise the hardware '''
        self._hwreset()        # Hardware reset. Blocks 3ms
        cmd = self._wcmd
        wcd = self._wcd
        cmd(b"\x01")           # SW reset datasheet specifies 120ms before SLPOUT
        sleep_ms(150)
        cmd(b"\x11")           # SLPOUT: exit sleep mode
        sleep_ms(10)           # Adafruit delay 500ms (datsheet 5ms)
        wcd(b"\x3a", b"\x55")  # _COLMOD 16 bit/pixel, 65Kbit color space
        cmd(b"\x21")           # INVOFF Adafruit turn inversion on. This driver fixes .rgb
        cmd(b"\x13")           # NORON Normal display mode
        # Set display window depending on mode, .height and .width.
        self.set_frame()
#         wcd(b"\x36", int.to_bytes(MODE[self.mode], 1, "little"))
        cmd(b"\x29")  # DISPON. Adafruit then delay 500ms.

    def turn_on(self):
        ''' Turn on backlight '''
        self._bl(1)
    
    def turn_off(self):
        ''' Turn off backlight '''
        self._bl(0)

    def set_frame(self):
        ''' set window to full frame '''
        if self.mode < 4:
            self.x_s, self.x_w = 35, 170
            self.y_s, self.y_w = 0, 320
        else:
            self.x_s, self.x_w = 0, 320
            self.y_s, self.y_w = 35, 170
        
        # Col address set.
        self._wcd(b"\x2a", pack(b'>HH', self.x_s, self.x_s + self.x_w))
        # Row address set
        self._wcd(b"\x2b", pack(b'>HH', self.y_s, self.y_s + self.y_w))
        # change mode
        self._wcd(b"\x36", int.to_bytes(MODE[self.mode], 1, "little"))
    
    def change_mode(self, mode):
        ''' Change display mode '''
        if mode < 0 or mode > 7:
            print(mode, " is not a valid mode !")
            return
        self.mode = mode
        self.set_frame()
    
    def set_window(self, xs, ys, xe, ye):
        ''' set widow to rectangle '''
        # Col address set.
        self._wcd(b"\x2a", pack(b'>HH', self.x_s + xs, self.x_s + xe))
        # Row address set
        self._wcd(b"\x2b", pack(b'>HH', self.y_s + ys, self.y_s + ye))
        
    def fill_rect(self, x, y, w, h, color):
        ''' fill rectangle with color '''
        self.set_window(x, y, x + w - 1, y + h - 1)
        chunks, rest = divmod(w * h * 2, _BUFFER_SIZE)
        self._dc(0)
        self._cs(0)
        self._spi.write(b"\x2c")
        self._dc(1)
        if chunks:
            self.buf[:] = color * (_BUFFER_SIZE//2)
            for _ in range(chunks):
                self._spi.write(self.buf)
        if rest:
            self.buf[:] = color * rest
            self._spi.write(self.buf)
        self._cs(0)

    def vline(self, x, y, length, color):
        """ Draw vertical line """
        self.fill_rect(x, y, 1, length, color)

    def hline(self, x, y, length, color):
        """ Draw horizontal line at the given location and color """
        self.fill_rect(x, y, length, 1, color)

    def pixel(self, x, y, color):
        """ Draw a pixel """
        self.set_window(x, y, x, y)
        self._wcd(b"\x2c", color)
    
    def clear(self, color=BLACK):
        ''' fill frame with color '''
        self.fill_rect(0, 0, self.x_w, self.y_w, color)
    
    def rect(self, x, y, w, h, color):
        """ Draw a rectangle """
        self.hline(x, y, w, color)
        self.vline(x, y, h, color)
        self.vline(x + w - 1, y, h, color)
        self.hline(x, y + h - 1, w, color)

    def line(self, x0, y0, x1, y1, color):
        """ Draw a single pixel wide line starting
            at x0, y0 and ending at x1, y1 """
        steep = abs(y1 - y0) > abs(x1 - x0)
        if steep:
            x0, y0 = y0, x0
            x1, y1 = y1, x1
        if x0 > x1:
            x0, x1 = x1, x0
            y0, y1 = y1, y0
        dx = x1 - x0
        dy = abs(y1 - y0)
        err = dx // 2
        ystep = 1 if y0 < y1 else -1
        while x0 <= x1:
            if steep:
                self.pixel(y0, x0, color)
            else:
                self.pixel(x0, y0, color)
            err -= dy
            if err < 0:
                y0 += ystep
                err += dx
            x0 += 1
    
    def circle(self, xc, yc, r, color):
        ''' Draw a circle '''
        f = 1 - r
        ddF_x = 1
        ddF_y = -2 * r
        x = 0
        y = r
        self.pixel(xc  , yc+r, color)
        self.pixel(xc  , yc-r, color)
        self.pixel(xc+r, yc  , color)
        self.pixel(xc-r, yc  , color)
        while x < y:
            if f >= 0:
                y -= 1
                ddF_y += 2
                f += ddF_y
            x += 1
            ddF_x += 2
            f += ddF_x
            self.pixel(xc + x, yc + y, color)
            self.pixel(xc - x, yc + y, color)
            self.pixel(xc + x, yc - y, color)
            self.pixel(xc - x, yc - y, color)
            self.pixel(xc + y, yc + x, color)
            self.pixel(xc - y, yc + x, color)
            self.pixel(xc + y, yc - x, color)
            self.pixel(xc - y, yc - x, color)
    
    def arc(self, xc, yc, r, alpha1, alpha2, color):
        ''' Draw arc [alpha1;alpha2]
                alpha1 < alpha2 in [-180°;180°] '''
        def set_pixel(xc, yc, x, y, alpha1, alpha2, color):
            if (-alpha2 <= atan2(y, x)) and (atan2(y, x) <= -alpha1):
                self.pixel(x+xc, y+yc, color)

        f = 1 - r
        ddF_x = 1
        ddF_y = -2 * r
        x = 0
        y = r

        alpha1 *= pi/180
        alpha2 *= pi/180

        set_pixel( xc, yc,  0,  r, alpha1, alpha2, color)
        set_pixel( xc, yc,  0, -r, alpha1, alpha2, color)
        set_pixel( xc, yc,  r,  0, alpha1, alpha2, color)
        set_pixel( xc, yc, -r,  0, alpha1, alpha2, color)

        while x < y:
            if f >= 0:
                y -= 1
                ddF_y += 2
                f += ddF_y
            x += 1
            ddF_x += 2
            f += ddF_x

            set_pixel(xc, yc,  x,  y, alpha1, alpha2, color)
            set_pixel(xc, yc, -x,  y, alpha1, alpha2, color)
            set_pixel(xc, yc,  x, -y, alpha1, alpha2, color)
            set_pixel(xc, yc, -x, -y, alpha1, alpha2, color)
            set_pixel(xc, yc,  y,  x, alpha1, alpha2, color)
            set_pixel(xc, yc, -y,  x, alpha1, alpha2, color)
            set_pixel(xc, yc,  y, -x, alpha1, alpha2, color)
            set_pixel(xc, yc, -y, -x, alpha1, alpha2, color)

    def round_box(self, x, y, width, height, r, color):
        ''' Draw rectangle with round corners '''
        if 2*r > min(width, height): r = min(width, height)//2
        self.hline(x+r, y, width-2*r, color)
        self.vline(x, y+r, height-2*r, color)
        self.vline(x+width, y+r, height-2*r, color)
        self.hline(x+r, y+height, width-2*r, color)
        self.arc(x+r, y+r, r, 90, 180, color)
        self.arc(x+width-r, y+r, r, 0, 90, color)
        self.arc(x+r, y+height-r, r, -180, -90, color)
        self.arc(x+width-r, y+height-r, r, -90, 0, color)
        
    def blit_buffer(self, buffer, x, y, width, height):
        ''' Copy buffer to rectangle '''
        self.set_window(x, y, x + width - 1, y + height - 1)
        self._dc(0)
        self._cs(0)
        self._spi.write(b"\x2c")
        self._dc(1)
        self._spi.write(buffer)
        self._cs(0)
    
    @micropython.viper
    @staticmethod
    def _pack8(glyphs, idx: uint, fg_color: uint, bg_color: uint):
        """ Pack a character into a byte array.

        Args:
            char (str): character to pack

        Returns:
            character bitmap in color565 format
        """
        buffer = bytearray(128)
        bitmap = ptr16(buffer)
        glyph = ptr8(glyphs)

        for i in range(0, 64, 8):
            byte = glyph[idx]
            bitmap[i] = fg_color if byte & _BIT7 else bg_color
            bitmap[i + 1] = fg_color if byte & _BIT6 else bg_color
            bitmap[i + 2] = fg_color if byte & _BIT5 else bg_color
            bitmap[i + 3] = fg_color if byte & _BIT4 else bg_color
            bitmap[i + 4] = fg_color if byte & _BIT3 else bg_color
            bitmap[i + 5] = fg_color if byte & _BIT2 else bg_color
            bitmap[i + 6] = fg_color if byte & _BIT1 else bg_color
            bitmap[i + 7] = fg_color if byte & _BIT0 else bg_color
            idx += 1

        return buffer

    @micropython.viper
    @staticmethod
    def _pack16(glyphs, idx: uint, fg_color: uint, bg_color: uint):
        """ Pack a character into a byte array.

        Args:
            char (str): character to pack

        Returns:
            character bitmap in color565 format
        """
        buffer = bytearray(256)
        bitmap = ptr16(buffer)
        glyph = ptr8(glyphs)

        for i in range(0, 128, 16):
            byte = glyph[idx]

            bitmap[i] = fg_color if byte & _BIT7 else bg_color
            bitmap[i + 1] = fg_color if byte & _BIT6 else bg_color
            bitmap[i + 2] = fg_color if byte & _BIT5 else bg_color
            bitmap[i + 3] = fg_color if byte & _BIT4 else bg_color
            bitmap[i + 4] = fg_color if byte & _BIT3 else bg_color
            bitmap[i + 5] = fg_color if byte & _BIT2 else bg_color
            bitmap[i + 6] = fg_color if byte & _BIT1 else bg_color
            bitmap[i + 7] = fg_color if byte & _BIT0 else bg_color
            idx += 1

            byte = glyph[idx]
            bitmap[i + 8] = fg_color if byte & _BIT7 else bg_color
            bitmap[i + 9] = fg_color if byte & _BIT6 else bg_color
            bitmap[i + 10] = fg_color if byte & _BIT5 else bg_color
            bitmap[i + 11] = fg_color if byte & _BIT4 else bg_color
            bitmap[i + 12] = fg_color if byte & _BIT3 else bg_color
            bitmap[i + 13] = fg_color if byte & _BIT2 else bg_color
            bitmap[i + 14] = fg_color if byte & _BIT1 else bg_color
            bitmap[i + 15] = fg_color if byte & _BIT0 else bg_color
            idx += 1

        return buffer

    def _text8(self, font, text, x0, y0, fg_color=WHITE, bg_color=BLACK):
        """
        Internal method to write characters with width of 8 and
        heights of 8 or 16.

        Args:
            font (module): font module to use
            text (str): text to write
            x0 (int): column to start drawing at
            y0 (int): row to start drawing at
            color (int): 565 encoded color to use for characters
            background (int): 565 encoded color to use for background
        """

        for char in text:
            ch = ord(char)
            if (
                font.FIRST <= ch < font.LAST
                and x0 + font.WIDTH <= self.x_w
                and y0 + font.HEIGHT <= self.y_w
            ):
                if font.HEIGHT == 8:
                    passes = 1
                    size = 8
                    each = 0
                else:
                    passes = 2
                    size = 16
                    each = 8

                for line in range(passes):
                    idx = (ch - font.FIRST) * size + (each * line)
                    buffer = self._pack8(font.FONT, idx, fg_color, bg_color)
                    self.blit_buffer(buffer, x0, y0 + 8 * line, 8, 8)

                x0 += 8

    def _text16(self, font, text, x0, y0, fg_color=WHITE, bg_color=BLACK):
        """
        Internal method to draw characters with width of 16 and heights of 16
        or 32.

        Args:
            font (module): font module to use
            text (str): text to write
            x0 (int): column to start drawing at
            y0 (int): row to start drawing at
            color (int): 565 encoded color to use for characters
            background (int): 565 encoded color to use for background
        """

        for char in text:
            ch = ord(char)
            if (
                font.FIRST <= ch < font.LAST
                and x0 + font.WIDTH <= self.x_w
                and y0 + font.HEIGHT <= self.y_w
            ):
                each = 16
                if font.HEIGHT == 16:
                    passes = 2
                    size = 32
                else:
                    passes = 4
                    size = 64

                for line in range(passes):
                    idx = (ch - font.FIRST) * size + (each * line)
                    buffer = self._pack16(font.FONT, idx, fg_color, bg_color)
                    self.blit_buffer(buffer, x0, y0 + 8 * line, 16, 8)
            x0 += 16

    def text(self, font, text, x0, y0, color=WHITE, background=BLACK):
        """
        Draw text on display in specified font and colors. 8 and 16 bit wide
        fonts are supported.

        Args:
            font (module): font module to use.
            text (str): text to write
            x0 (int): column to start drawing at
            y0 (int): row to start drawing at
            color (int): 565 encoded color to use for characters
            background (int): 565 encoded color to use for background
        """
        fg_color = (color[1] << 8) + color[0]
        bg_color = (background[1] << 8) + background[0]

        if font.WIDTH == 8:
            self._text8(font, text, x0, y0, fg_color, bg_color)
        else:
            self._text16(font, text, x0, y0, fg_color, bg_color)
