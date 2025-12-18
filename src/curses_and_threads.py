import curses
import threading
import time


def worker(w, msg, run, lock):
    val = 1
    while run["run"]:
        with lock:
            w.addstr(1, 1, msg + " " + str(val))
            w.refresh()
        val += 1
        if val > 999:
            val = 1
        time.sleep(1)


def runner(w, run, lock):
    x = 1
    y = 1
    my, mx = w.getmaxyx()
    while run["run"]:
        with lock:
            w.addch(y, x, curses.ACS_RARROW)
            w.refresh()
        time.sleep(0.1)
        with lock:
            w.addstr(y, x, " ")
        x += 1
        if x > mx - 2:
            x = 1
            y += 1
            if y > my - 2:
                y = 1


def move(x, y, dx, dy, mx, my):
    x += dx
    if not 2 <= x <= mx - 3:
        dx *= -1
    y += dy
    if not 2 <= y <= my - 3:
        dy *= -1

    return x, y, dx, dy


def pong(w, directions, run, lock):
    x = 1
    y = 1
    dx = 1
    dy = 1
    my, mx = w.getmaxyx()
    w.addstr(1, 1, f"my:{my},mx:{mx}")
    while run["run"]:
        ch = directions[(dx, dy)]
        with lock:
            w.addch(y, x, ch)
            w.refresh()
        time.sleep(0.1)
        with lock:
            w.addstr(y, x, " ")
        (
            x,
            y,
            dx,
            dy,
        ) = move(x, y, dx, dy, mx, my)


def main(screen):
    curses.start_color()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLUE)
    curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.curs_set(0)
    screen.refresh()

    direction_chars = {
        (1, 1): curses.ACS_LRCORNER,
        (-1, 1): curses.ACS_LLCORNER,
        (-1, -1): curses.ACS_ULCORNER,
        (1, -1): curses.ACS_URCORNER,
    }

    current_x = 1
    window_specs = [
        (10, 10, 3, "hi"),
        (10, 10, 1, None),
        (10, 10, 2, None),
        (10, 25, 4, None),
        (15, 28, 3, None),
    ]
    windows = []
    for height, width, color, label in window_specs:
        win = curses.newwin(height, width, 1, current_x)
        win.bkgd(curses.color_pair(color))
        win.box()
        if label:
            win.addstr(1, 1, label)
        win.refresh()
        windows.append(win)
        current_x += width
    win, win1, win2, win3, win4 = windows

    state = {"run": True}
    lock = threading.Lock()
    threads = [
        threading.Thread(target=worker, args=(win1, "win1", state, lock)),
        threading.Thread(target=worker, args=(win2, "win2", state, lock)),
        threading.Thread(target=runner, args=(win3, state, lock)),
        threading.Thread(target=pong, args=(win4, direction_chars, state, lock)),
    ]
    try:
        for t in threads:
            t.start()
    except:
        win.addstr(2, 1, "failed")

    c = screen.getch()
    state["run"] = False


try:
    curses.wrapper(main)
except:
    print("hmmm")

print("stopping")
