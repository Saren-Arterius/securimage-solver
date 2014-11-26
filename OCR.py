#!/usr/bin/env python3
from os.path import dirname, join, realpath
from json import loads, dumps
from re import findall

script_path = dirname(realpath(__file__))


class OCRStorage(object):
    GRID_SIZE = 30

    @staticmethod
    def load_db():
        try:
            return loads(open(join(script_path, "chars_db.json")).read())
        except FileNotFoundError:
            chars = {"-": [[0] * OCRStorage.GRID_SIZE for i in range(OCRStorage.GRID_SIZE)]}
            chars["-"][0][0] = 1
            with open(join(script_path, "chars_db.json"), "w+") as db_file:
                db_file.write(dumps(chars))
            return chars

    @staticmethod
    def save_db(db):
        with open(join(script_path, "chars_db.json"), "w+") as db_file:
            db_file.write(dumps(db))


class OCR(object):
    chars_db = OCRStorage.load_db()
    GRID_SIZE = 30

    def __init__(self, char_grid):
        assert len(char_grid) == OCR.GRID_SIZE
        for row in char_grid:
            assert len(row) == OCR.GRID_SIZE
        self.char_grid = char_grid

    def train_char(self, char):
        assert len(char) == 1 and findall("[a-zA-Z0-9]", char)
        if char in OCR.chars_db:
            for x in range(OCR.GRID_SIZE):
                for y in range(OCR.GRID_SIZE):
                    OCR.chars_db[char][y][x] += self.char_grid[y][x]
        else:
            OCR.chars_db[char] = self.char_grid
        OCRStorage.save_db(OCR.chars_db)

    def match_char(self):
        matches = {}
        for char, grid in OCR.chars_db.items():
            current_value = 0
            value_total = 0
            for x in range(OCR.GRID_SIZE):
                for y in range(OCR.GRID_SIZE):
                    value_total += grid[y][x]
                    if self.char_grid[y][x] == 1 and grid[y][x] >= 1:
                        current_value += grid[y][x]
                    elif self.char_grid[y][x] == 1 and grid[y][x] == 0:
                        current_value *= 0.975
                    else:
                        current_value -= grid[y][x]
            matches[char] = current_value / value_total
        # print("Should be {0}: {1}".format(max(matches, key = lambda x: matches[x[0]]), repr(matches)))
        return max(matches, key = lambda x: matches[x[0]])