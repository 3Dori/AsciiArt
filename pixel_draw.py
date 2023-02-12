from PIL import Image
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
        self.load_chars_with_font(fontpath, fontsize)
        self._compute_charset_features()

    def image_to_ascii(self, imagepath, scale=None, linespacing=0.8, reverse_color=True):
        arr = self._load_image_arr_monochrome(imagepath, scale, linespacing)
        canvas_h, canvas_w = arr.shape[0] // self._h, arr.shape[1] // self._w
        ascii_canvas = np.zeros((canvas_h, canvas_w), dtype=str)
        for x in range(canvas_w):
            for y in range(canvas_h):
                block = arr[y*self._h:y*self._h+self._h, x*self._w:x*self._w+self._w]
                char = self._find_best_matched_char(block, reverse_color)
                ascii_canvas[y, x] = char
        self._print_canvas(ascii_canvas)

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

    def load_chars_with_font(self, fontpath, fontsize, filters=None):
        from PIL import ImageFont

        self._char_to_arr = {}
        self.font = ImageFont.truetype(fontpath, fontsize)
        MONOSPACED_CHAR = ' '
        self._w, self._h = self.font.getsize(MONOSPACED_CHAR)

        for char in self.CHARSET:
            self._load_char(char, filters)
    
    def _load_char(self, char, filters=None):
        from PIL import ImageDraw

        image = Image.new('L', (self._w, self._h), 0)
        draw = ImageDraw.Draw(image)
        draw.text((0, 0), text=char, font=self.font, fill="white")
        if filters:
            for filter in filters:
                image = image.filter(filter)
        self._char_to_arr[char] = np.asarray(image)


class BrightnessPixelDraw(_PixelDraw):
    def _compute_charset_features(self):
        char_to_brightness = {char: self._get_brightness(arr)
                              for char, arr in self._char_to_arr.items()}
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


class MinDiffPixelDraw(_PixelDraw):
    CHARSET = string.ascii_letters + string.digits + string.punctuation + ' '

    def __init__(self, fontpath='Menlo.ttc', fontsize=14, filter_radius=1.3):
        self._filter_radius = filter_radius
        super().__init__(fontpath, fontsize)

    def _compute_charset_features(self):
        from PIL import ImageFilter
        filters = [ImageFilter.GaussianBlur(self._filter_radius)]
        for char in self.CHARSET:
            self._load_char(char, filters)
        self._char_arr = np.array([arr for arr in self._char_to_arr.values()])
        self._char_arr_reversed = 255 - self._char_arr

    def _find_best_matched_char(self, block, reversed_color=True):
        char_arr = self._char_arr_reversed if reversed_color else self._char_arr
        min_idx = np.argmin(np.linalg.norm(block - char_arr, axis=(1, 2)))
        return self.CHARSET[min_idx]
