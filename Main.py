#!/usr/bin/env python3
from queue import Queue
from threading import Thread
from urllib.request import urlopen
from os.path import dirname, realpath
from io import BytesIO
import tkinter

from PIL import Image, ImageTk

from Solver import Solver

script_path = dirname(realpath(__file__))
captcha_url = "https://saren.wtako.net/securimage/securimage_show.php"
captcha_length = 6


class CaptchaGatherThread(Thread):

    captchas = Queue(10)

    def __init__(self):
        super(CaptchaGatherThread, self).__init__(daemon = True)

    def run(self):
        while True:
            solver = None
            while solver is None or len(solver.char_areas) != captcha_length:
                rep = urlopen(captcha_url)
                answer = rep.info()['x-captcha-code']
                print(answer)
                buffer = BytesIO(rep.read())
                solver = Solver(Image.open(buffer), captcha_length)
            buffer.seek(0)
            captcha_result = solver.get_result()
            CaptchaGatherThread.captchas.put({"captcha": Image.open(buffer), "solver": solver, "guess": captcha_result, "answer": answer})
            print('Put')


class CaptchaInputWindow(object):
    def __init__(self, parent):
        self.parent = parent
        self.hint = tkinter.StringVar()
        self.hint.set("Type in 6 characters to train.\nWhat characters did you see in the image below?")
        tkinter.Label(self.parent, textvariable = self.hint).pack()
        self.captcha_display = tkinter.Label(self.parent)
        self.captcha_display.pack()
        self.captcha_cleaned_display = tkinter.Label(self.parent)
        self.captcha_cleaned_display.pack()
        self.result = tkinter.StringVar()
        self.result.set("")
        tkinter.Label(self.parent, textvariable = self.result).pack()
        self.interactive = tkinter.StringVar()
        self.interactive.set("")
        tkinter.Label(self.parent, textvariable = self.interactive).pack()
        self.acc = tkinter.StringVar()
        self.acc.set("")
        tkinter.Label(self.parent, textvariable = self.acc).pack()
        self.entry = tkinter.Entry(self.parent)
        self.entry.pack()
        self.entry.focus_set()
        self.yes_button = tkinter.Button(self.parent, text = "Fucking yes!", width = 10, command = self.yes)
        self.yes_button.pack()
        self.entry_send = tkinter.Button(self.parent, text = "Train", width = 10, command = self.entry_callback)
        self.entry_send.pack()
        self.skip_button = tkinter.Button(self.parent, text = "Skip", width = 10, command = self.skip)
        self.skip_button.pack()
        self.solver = None
        self.captcha_guess = None
        self.guess = 0
        self.correct = 0
        self.another()

    def another(self):
        self.entry.delete(0, tkinter.END)

        solver_queue = CaptchaGatherThread.captchas.get()
        self.solver = solver_queue["solver"]
        self.captcha_guess = solver_queue["guess"]
        captcha_photo = ImageTk.PhotoImage(solver_queue["captcha"])
        self.captcha_display.configure(image = captcha_photo)
        self.captcha_display.image = captcha_photo
        captcha_cleaned_photo = ImageTk.PhotoImage(self.solver.captcha)
        self.captcha_cleaned_display.configure(image = captcha_cleaned_photo)
        self.captcha_cleaned_display.image = captcha_cleaned_photo
        self.captcha_guess = self.solver.get_result()
        self.result.set(self.captcha_guess)
        self.acc.set("{0}/{1} ({2}%)".format(self.correct, self.guess,
                                             round((self.correct / (self.guess if self.guess != 0 else 1) * 100),
                                                   2)))
        self.guess += 1
        self.parent.update()
        CaptchaGatherThread.captchas.task_done()

        self.solver.train(solver_queue["answer"])
        self.interactive.set("Thought: {0}, Trained: {1}".format(self.captcha_guess, solver_queue["answer"]))
        self.another()

    def entry_callback(self):
        if len(self.entry.get()) != captcha_length:
            return self.skip()
        self.solver.train(self.entry.get())
        self.interactive.set("Thought: {0}, Trained: {1}".format(self.captcha_guess, self.entry.get()))
        self.another()

    def skip(self):
        self.interactive.set("Skipped.")
        self.another()

    def yes(self):
        self.correct += 1
        self.solver.train(self.captcha_guess)
        self.interactive.set("Answer: {0} - I am so awesome.".format(self.captcha_guess))
        self.another()


if __name__ == "__main__":
    for i in range(12):
        CaptchaGatherThread().start()
    root = tkinter.Tk()
    CaptchaInputWindow(root)
    tkinter.mainloop()
