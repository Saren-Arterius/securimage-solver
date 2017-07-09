#!/usr/bin/env python3
from multiprocessing import Process, Queue
from io import BytesIO
from threading import Thread
from urllib.request import build_opener, HTTPCookieProcessor
from urllib.parse import urlencode
import tkinter
from http.cookiejar import CookieJar

from PIL import Image, ImageTk
from pyquery import PyQuery as pq

from Solver import Solver

host = "https://saren.wtako.net"
captcha_url = "https://saren.wtako.net/securimage/example_form.php"
captcha_length = 6


class CaptchaInputWindow(object):
    def __init__(self, parent):
        self.parent = parent
        self.hint = tkinter.StringVar()
        self.hint.set("Watch the computer trying to solve captchas.")
        tkinter.Label(self.parent, textvariable = self.hint).pack()
        self.captcha_display = tkinter.Label(self.parent)
        self.captcha_display.pack()
        self.captcha_cleaned_display = tkinter.Label(self.parent)
        self.captcha_cleaned_display.pack()
        self.result = tkinter.StringVar()
        self.result.set("")
        tkinter.Label(self.parent, textvariable = self.result).pack()
        self.acc = tkinter.StringVar()
        self.acc.set("")
        tkinter.Label(self.parent, textvariable = self.acc).pack()
        self.trials = 0
        self.success = 0
        self.prefail = 0
        Thread(target = self.update, daemon = True).start()

    def update(self):
        while True:
            trial = captcha_queue.get()
            print("got")
            if not trial[4]:
                self.another(trial[0], Image.frombytes(trial[1]['mode'], trial[1]['size'], trial[1]['pixels']),
                             trial[2],
                             trial[3], trial[4])
            else:
                self.another(trial[0], trial[1], trial[2], trial[3], trial[4])

    def another(self, orig, cleaned, guess, success, prefail):
        captcha_photo = ImageTk.PhotoImage(orig)
        self.captcha_display.configure(image = captcha_photo)
        self.captcha_display.image = captcha_photo
        captcha_cleaned_photo = ImageTk.PhotoImage(cleaned)
        self.captcha_cleaned_display.configure(image = captcha_cleaned_photo)
        self.captcha_cleaned_display.image = captcha_cleaned_photo
        self.result.set(guess)
        if success:
            self.success += 1
        if prefail:
            self.prefail += 1
        else:
            self.trials += 1
        if self.trials != 0:
            self.acc.set(
                "{0}/{1}/{2}\nHitrate: {3}% ({4}%)".format(self.success, self.trials, self.trials + self.prefail,
                                                           round((self.success / self.trials) * 100, 2),
                                                           round((self.success / (self.trials + self.prefail)) * 100, 2)))
        self.parent.update()


class CaptchaSolveProcess(Process):
    def __init__(self, queue):
        super(CaptchaSolveProcess, self).__init__(daemon = True)
        self.queue = queue
        self.opener = build_opener(HTTPCookieProcessor(CookieJar()))

    def run(self):
        while True:
            html = self.opener.open(captcha_url).read().decode()
            captcha_img_url = host + pq(html)("#captcha_image").attr("src")
            captcha_img = self.opener.open(captcha_img_url).read()
            try:
                solver = Solver(Image.open(BytesIO(captcha_img)), captcha_length)
                result = solver.get_result()
                if len(solver.char_areas) != captcha_length:
                    raise IndexError()
            except IndexError:
                self.queue.put(
                    (Image.open(BytesIO(captcha_img)), Image.open(BytesIO(captcha_img)), "------", False, True))
                continue
            payload = {
                "do": "contact",
                "ct_name": "",
                "ct_email": "",
                "ct_URL": "",
                "ct_message": "",
                "ct_captcha": result
            }
            resp = self.opener.open(captcha_url, urlencode(payload).encode()).read().decode()
            print("put!")
            img_data = {
                'pixels': solver.captcha.tobytes(),
                'size': solver.captcha.size,
                'mode': solver.captcha.mode,
            }
            if "captcha was correct" in resp:
                self.queue.put((Image.open(BytesIO(captcha_img)), img_data, result, True, False))
                print('Corr')
            else:
                self.queue.put((Image.open(BytesIO(captcha_img)), img_data, result, False, False))
                print('Wong')


if __name__ == "__main__":
    captcha_queue = Queue()
    for i in range(12):
        CaptchaSolveProcess(captcha_queue).start()
    root = tkinter.Tk()
    window = CaptchaInputWindow(root)
    tkinter.mainloop()
