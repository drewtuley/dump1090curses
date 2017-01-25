import curses
import threading
import time


def worker(w, msg, run):
    val = 1
    while run['run']:
        w.addstr(1, 1, msg + ' ' + str(val))
        w.refresh()
        val += 1
        time.sleep(1)


def runner(w, run):
    x = 1
    y = 1
    while run['run']:
        #w.addstr(y,x, '*')
        w.addch(y, x, 42)
        w.refresh()
        time.sleep(0.1)
        w.addstr(y,x, ' ')
        x += 1
        if x > 18:
            x = 1
            y += 1
            if y > 8:
                y = 1


def move(x, y, dx, dy):
    x += dx
    if x > 17 or x < 2:
        dx *= -1
    y += dy
    if y > 7 or y < 2:
        dy *= -1

    return (x, y, dx, dy)


def pong(w, run):
    x = 1
    y = 1
    dx = 1
    dy = 1
    while run['run']:
        #w.addstr(y,x, '*')
        w.addch(y, x, 42)
        w.refresh()
        time.sleep(0.1)
        w.addstr(y,x, ' ')
        x, y, dx, dy, = move(x, y, dx, dy)



def main(screen):
    curses.start_color()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLUE)
    curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.curs_set(0)
    screen.refresh()

    win = curses.newwin(10, 10, 1, 1)
    win.bkgd(curses.color_pair(3))
    win.box()

    win.addstr(1, 1, 'hi')
    win.refresh()

    win1 = curses.newwin(10, 10, 1, 11)
    win1.bkgd(curses.color_pair(1))
    win1.box()

    win2 = curses.newwin(10, 10, 1, 21)
    win2.bkgd(curses.color_pair(2))
    win2.box()

    win3 = curses.newwin(10, 20, 1, 31)
    win3.bkgd(curses.color_pair(4))
    win3.box()

    win4 = curses.newwin(10, 20, 1, 51)
    win4.bkgd(curses.color_pair(3))
    win4.box()

    state = {'run': True}
    threads = [
        threading.Thread(target=worker, args=(win1, 'win1', state)),
        threading.Thread(target=worker, args=(win2, 'win2', state)),
        threading.Thread(target=runner, args=(win3, state)),
        threading.Thread(target=pong, args=(win4, state))
    ]
    try:
        for t in threads:
            t.start()
    except:
        win.addstr(2, 1, 'failed')

    c = screen.getch()
    state['run'] = False
try:
    curses.wrapper(main)
except:
    print 'hmmm'

print 'stopping'

