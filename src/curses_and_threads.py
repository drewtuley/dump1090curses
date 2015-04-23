import curses
import threading,time


def worker(w,msg,run):
    val=1
    while run['run']:
        w.addstr(1,1,msg+' '+str(val))
        w.refresh()
        val += 1
        time.sleep(1)

def main(screen):
    curses.start_color()
    curses.init_pair(1,curses.COLOR_WHITE, curses.COLOR_BLACK)
    screen.refresh()

    win = curses.newwin(10,10,1,1)
    win.bkgd(curses.color_pair(1))
    win.box()

    win.addstr(1,1,'hi')
    win.refresh()

    win1 = curses.newwin(10,10,1,11)
    win1.bkgd(curses.color_pair(1))
    win1.box()

    win2 = curses.newwin(10,10,1,21)
    win2.bkgd(curses.color_pair(1))
    win2.box()

    state={'run': True}
    try:
        t1 = threading.Thread(target=worker, args=(win1,'win1',state ))
        t2 = threading.Thread(target=worker, args=(win2,'win2',state ))
        t1.start()
        t2.start()
    except:
        win.addstr(2,1,'failed')

    c=screen.getch()
    state['run']=False
try:
    curses.wrapper(main)
except:
    print 'hmmm'

print 'stopping'

