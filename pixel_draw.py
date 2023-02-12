from PIL import Image
# from PIL import ImageFilter
import numpy as np

import string
import bisect


class _PixelDraw:
    CHARSET = ' 1234567890!@#$%^&*().awjiWMXQ[]='

    def _compute_charset_features(self):
        pass

    def _find_best_matched_char(self, block):
        pass

    def __init__(self, fontpath='Menlo.ttc', fontsize=14):
        from PIL import ImageFilter

        self.load_chars_with_font(fontpath, fontsize,
                                  filters=[ImageFilter.GaussianBlur(1.0)])
        self._compute_charset_features()

    @staticmethod
    def _load_image_arr_monochrome(imagepath, scale=None, linespacing=None):
        image = Image.open(imagepath)
        image = image.convert('L')
        if scale or linespacing:
            if scale is None:
                scale = 1
            if linespacing is None:
                linespacing = 1
            new_width = round(image.width * scale)
            new_height = round(image.height * scale * linespacing)
            image = image.resize((new_width, new_height))
        return np.asarray(image)

    @staticmethod
    def _print_canvas(canvas: np.array):
        for row in canvas:
            print(''.join(row))

    def image_to_ascii(self, imagepath, scale=None, linespacing=0.8, reverse_color=True):
        arr = self._load_image_arr_monochrome(imagepath, scale, linespacing)
        canvas_h, canvas_w = arr.shape[0] // self.h, arr.shape[1] // self.w
        ascii_canvas = np.zeros((canvas_h, canvas_w), dtype=str)
        for x in range(canvas_w):
            for y in range(canvas_h):
                block = arr[y*self.h:y*self.h+self.h, x*self.w:x*self.w+self.w]
                char = self._find_best_matched_char(block, reverse_color)
                ascii_canvas[y, x] = char
        self._print_canvas(ascii_canvas)

    def load_chars_with_font(self, fontpath, fontsize, filters=None):
        from PIL import ImageFont

        self.char_to_arr = {}
        font = ImageFont.truetype(fontpath, fontsize)
        MONOSPACED_CHAR = ' '
        self.w, self.h = font.getsize(MONOSPACED_CHAR)

        for char in self.CHARSET:
            self._load_char(char, font, filters)
    
    def _load_char(self, char, font, filters=None):
        from PIL import ImageDraw

        image = Image.new('L', (self.w, self.h), 0)
        draw = ImageDraw.Draw(image)
        draw.text((0, 0), text=char, font=font, fill="white")
        if filters:
            for filter in filters:
                image = image.filter(filter)
        self.char_to_arr[char] = np.asarray(image)


class BrightnessPixelDraw(_PixelDraw):
    def _compute_charset_features(self):
        char_to_brightness = {char: self._get_brightness(arr)
                              for char, arr in self.char_to_arr.items()}
        brightnesses = sorted(char_to_brightness.items(),
                              key=lambda pair_char_brightness: pair_char_brightness[1],
                              reverse=True)
        lightest, darkest = brightnesses[0][1], brightnesses[-1][1]

        def scale_brightness(brightness, reverse_color=True):
            brightness = (brightness - darkest) / (lightest - darkest) * 255
            return 255 - brightness if reverse_color else brightness

        self._brightnesses_reversed = [(char, scale_brightness(brightness, reverse_color=True))
                                       for char, brightness in brightnesses]
        self._brightnesses =          [(char, scale_brightness(brightness, reverse_color=False))
                                       for char, brightness in brightnesses[::-1]]

    def _find_best_matched_char(self, block, reverse_color=True):
        brightness = self._get_brightness(block)
        brightnesses = self._brightnesses_reversed if reverse_color else self._brightnesses
        idx = bisect.bisect_left(brightnesses, brightness,
                                 key=lambda pair_char_brightness: pair_char_brightness[1])
        return brightnesses[idx][0]

    @staticmethod
    def _get_brightness(arr):
        "arr should be an image array in 'L' mode"
        return np.mean(arr)
