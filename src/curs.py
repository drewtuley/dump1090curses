#!/usr/bin/python

import curses
import time


def main(screen):
    curses.start_color()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLUE)

    screen.refresh()

    win = curses.newwin(10, 80, 5, 5)
    win.bkgd(curses.color_pair(1))
    win.box()
    win.addstr(2, 2, "hi")
    win.refresh()
    x = 1
    while x < 10:
        time.sleep(1)
        win.erase()
        win.addstr(2, 2, str(x))
        win.refresh()
        x = x + 1

    c = screen.getch()


try:
    curses.wrapper(main)
except KeyboardInterrupt:
    exit()
