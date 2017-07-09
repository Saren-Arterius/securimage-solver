#!/usr/bin/env python3
import numpy
from scipy.misc import imresize
from enum import Enum

from PIL import Image

from OCR import OCR


class Solver(object):
    def __init__(self, captcha, chars_len):
        assert isinstance(captcha, Image.Image)
        self.chars_len = chars_len
        self.captcha = captcha.convert("L")
        self.anti_antialias(140, 8)
        self.remove_bad_colors()
        self.blacken()
        self.cut_chars(2)
        self.remove_lonely_pixels(32)
        self.char_areas = self.get_char_areas()

    def train(self, chars):
        for i, char in enumerate(chars):
            OCR(self.to_numberic_grid(i)).train_char(char)

    def get_result(self):
        return "".join([OCR(self.to_numberic_grid(i)).match_char() for i in range(self.chars_len)])

    def cut_chars(self, threshold):
        continuous_columns = []
        for x in range(self.captcha.size[0]):
            in_black = False
            for y in range(self.captcha.size[1]):
                if self.captcha.getpixel((x, y)) == Color.BLACK.value:
                    if not in_black:
                        in_black = True
                        continuous_columns.append([])
                    continuous_columns[len(continuous_columns) - 1].append((x, y))
                else:
                    in_black = False
        for continuous_column in continuous_columns:
            if len(continuous_column) < threshold:
                for xy in continuous_column:
                    self.captcha.putpixel(xy, Color.WHITE.value)

    def get_char_areas(self):
        areas = []
        searched = []
        for x in range(self.captcha.size[0]):
            for y in range(self.captcha.size[1]):
                if (x, y) in searched or self.captcha.getpixel((x, y)) == Color.WHITE.value:
                    continue
                result = self.recursively_find_near_pixels([(x, y)], Color.BLACK.value, True, 0)
                min_x, min_y, max_x, max_y = self.captcha.size[0], self.captcha.size[1], 0, 0
                for xy in result:
                    searched.append(xy)
                    if xy[0] < min_x:
                        min_x = xy[0]
                    if xy[1] < min_y:
                        min_y = xy[1]
                    if xy[0] > max_x:
                        max_x = xy[0]
                    if xy[1] > max_y:
                        max_y = xy[1]
                areas.append(((min_x, min_y), (max_x, max_y)))
        return areas

    def to_numberic_grid(self, char_index):
        contain_size = max([self.char_areas[char_index][1][0] - self.char_areas[char_index][0][0],
                            self.char_areas[char_index][1][1] - self.char_areas[char_index][0][1]])
        grid = [[0] * contain_size for i in range(contain_size)]
        for x in range(self.char_areas[char_index][0][0], self.char_areas[char_index][1][0]):
            for y in range(self.char_areas[char_index][0][1], self.char_areas[char_index][1][1]):
                if self.captcha.getpixel((x, y)) == Color.BLACK.value:
                    grid[y - self.char_areas[char_index][0][1]][x - self.char_areas[char_index][0][0]] += 1
        img = numpy.array(grid)
        new_img = imresize(img, (OCR.GRID_SIZE, OCR.GRID_SIZE))
        new_grid = [[0] * OCR.GRID_SIZE for i in range(OCR.GRID_SIZE)]
        for x in range(OCR.GRID_SIZE):
            for y in range(OCR.GRID_SIZE):
                if new_img[y][x] > 0:
                    new_grid[y][x] = 1
        return new_grid

    def anti_antialias(self, target_color, strength):
        searched = []
        for x in range(self.captcha.size[0]):
            for y in range(self.captcha.size[1]):
                if self.captcha.getpixel((x, y)) != target_color:
                    continue
                if (x, y) in searched:
                    continue
                near_pixels = self.recursively_find_near_pixels([(x, y)], target_color, False, 0)
                for near_pixel in near_pixels:
                    searched.append(near_pixel)
                if len(near_pixels) < strength:
                    for near_pixel in near_pixels:
                        self.captcha.putpixel(near_pixel, Color.WHITE.value)

    def blacken(self):
        for x in range(self.captcha.size[0]):
            for y in range(self.captcha.size[1]):
                if self.captcha.getpixel((x, y)) != Color.WHITE.value:
                    self.captcha.putpixel((x, y), Color.BLACK.value)

    def remove_bad_colors(self):
        for x in range(self.captcha.size[0]):
            for y in range(self.captcha.size[1]):
                if self.captcha.getpixel((x, y)) < 128:
                    searched_pixels = []
                    grey_count = 0
                    white_count = 0
                    has_value = False
                    for search_x in range(x, self.captcha.size[0]):
                        searched_pixels.append((search_x, y))
                        color = self.captcha.getpixel((search_x, y))
                        if color == Color.WHITE.value:
                            white_count += 1
                            has_value = True
                        if color >= 128:
                            grey_count += 1
                            has_value = True
                        if has_value:
                            break
                    has_value = False
                    for search_x in range(x, 0, -1):
                        searched_pixels.append((search_x, y))
                        color = self.captcha.getpixel((search_x, y))
                        if color == Color.WHITE.value:
                            white_count += 1
                            break
                        if color >= 128:
                            grey_count += 1
                            break
                        if has_value:
                            break
                    has_value = False
                    for search_y in range(y, self.captcha.size[1]):
                        searched_pixels.append((x, search_y))
                        color = self.captcha.getpixel((x, search_y))
                        if color == Color.WHITE.value:
                            white_count += 1
                            break
                        if color >= 128:
                            grey_count += 1
                            break
                        if has_value:
                            break
                    has_value = False
                    for search_y in range(y, 0, -1):
                        searched_pixels.append((x, search_y))
                        color = self.captcha.getpixel((x, search_y))
                        if color == Color.WHITE.value:
                            white_count += 1
                            break
                        if color >= 128:
                            grey_count += 1
                            break
                        if has_value:
                            break
                    if grey_count < 3 or white_count > 2:
                        self.captcha.putpixel((x, y), Color.WHITE.value)
                    else:
                        self.captcha.putpixel((x, y), Color.BLACK.value)

    def remove_lonely_pixels(self, threshold):
        searched = []
        for x in range(self.captcha.size[0]):
            for y in range(self.captcha.size[1]):
                if (x, y) in searched or self.captcha.getpixel((x, y)) == Color.WHITE.value:
                    continue
                result = self.recursively_find_near_pixels([(x, y)], Color.BLACK.value, True, 0)
                for xy in result:
                    searched.append(xy)
                    if len(result) < threshold:
                        self.captcha.putpixel(xy, Color.WHITE.value)

    def fill_holes(self):
        for x in range(self.captcha.size[0]):
            for y in range(self.captcha.size[1]):
                if list(self.get_near_colors((x, y), True)).count(Color.BLACK.value) >= 3:
                    self.captcha.putpixel((x, y), Color.BLACK.value)

    def get_near_colors(self, xy, cross):
        colors = []
        for xy in self.get_near_pixels(xy, cross):
            colors.append(self.captcha.getpixel(xy))
        return colors

    def get_near_pixels(self, xy, cross):
        pixels = []
        for x_offset in range(-1, 2):
            for y_offset in range(-1, 2):
                if cross and abs(x_offset - y_offset) != 1:
                    continue
                elif x_offset == 0 and y_offset == 0:
                    continue
                if xy[0] + x_offset not in range(self.captcha.size[0]):
                    continue
                if xy[1] + y_offset not in range(self.captcha.size[1]):
                    continue
                pixels.append((xy[0] + x_offset, xy[1] + y_offset))
        return pixels

    def recursively_find_near_pixels(self, pixels, color, cross, length):
        for pixel in pixels:
            for offset_pixel in self.get_near_pixels(pixel, cross):
                if offset_pixel in pixels:
                    continue
                if self.captcha.getpixel(offset_pixel) == color:
                    pixels.append(offset_pixel)
        if len(pixels) == length:
            return pixels
        return self.recursively_find_near_pixels(pixels, color, cross, len(pixels))

    @staticmethod
    def is_good_color(color):
        if color < 128:
            return True
        return False


class Color(Enum):
    BLACK = 0
    WHITE = 255
