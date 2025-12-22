import curses
import threading
import time
from importlib.resources import open_text


def worker(w, msg, run, lock):
    val = 1
    while run["run"]:
        with lock:
            w.addstr(1, 1, "{0:} {1:>3s}".format(msg, str(val)))
            w.refresh()
        val += 1
        if val > 999:
            val = 1
        time.sleep(1)


def runner(w, run, lock):
    x, y, dx, dy = (1, 1, 1, 1)
    my, mx = w.getmaxyx()
    while run["run"]:
        with lock:
            w.addch(y, x, curses.ACS_RARROW if dx == 1 else curses.ACS_LARROW)
            w.refresh()
        time.sleep(0.1)
        with lock:
            w.addstr(y, x, " ")
        x += dx
        if x > mx - 2 or x < 1:
            x -= dx
            dx = -dx
            y += dy
            if y > my - 2 or y < 1:
                y -= dy
                dy = -dy


def draw_wall(w, wall, *walls):
    for y, x in wall[0]:
        w.addch(y, x, wall[1])
    for other_wall, other_line in walls:
        for y, x in other_wall:
            w.addch(y, x, other_line)


def pong(w, directions, run, lock):
    my, mx = w.getmaxyx()
    obstacles = set()

    v_wall1 = set((i, 5) for i in range(4, 12))
    v_wall2 = set((i, mx - 6) for i in range(4, 12))
    h_wall1 = set((int(my / 2), i) for i in range(12, mx - 10))
    h_wall2 = set((int(my / 2) + 4, i) for i in range(10, mx - 8))
    top_wall = set((0, i) for i in range(0, mx))
    bottom_wall = set((my - 1, i) for i in range(0, mx))
    left_wall = set((i, 0) for i in range(1, my))
    right_wall = set((i, mx - 1) for i in range(1, my))
    obstacles.update(top_wall)
    obstacles.update(bottom_wall)
    obstacles.update(left_wall)
    obstacles.update(right_wall)
    obstacles.update(v_wall1)
    obstacles.update(v_wall2)
    obstacles.update(h_wall1)
    obstacles.update(h_wall2)

    x, y, dx, dy = (1, 1, 1, 1)

    # w.addstr(1, 1, f"my:{my},mx:{mx}")
    while run["run"]:
        new_y, new_x = (y + dy, x + dx)
        if (new_y, new_x) in obstacles:
            if (
                (new_y, new_x) in top_wall
                or (new_y, new_x) in bottom_wall
                or (new_y, new_x) in h_wall1
                or (new_y, new_x) in h_wall2
            ):
                dy = -dy
            elif (
                (new_y, new_x) in left_wall
                or (new_y, new_x) in right_wall
                or (new_y, new_x) in v_wall1
                or (new_y, new_x) in v_wall2
            ):
                dx = -dx
        else:
            y, x = new_y, new_x
        ch = directions[(dx, dy)]
        with lock:
            w.addch(y, x, ch)
            draw_wall(
                w,
                (v_wall1, curses.ACS_VLINE),
                (v_wall2, curses.ACS_VLINE),
                (h_wall1, curses.ACS_HLINE),
                (h_wall2, curses.ACS_HLINE),
            )
            w.refresh()
        time.sleep(0.1)
        # with lock:
        #     w.addstr(y, x, " ")


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
        (16, 28, 3, None),
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
