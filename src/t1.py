#!/usr/bin/python
import threading


def t1(arg):
    print("my arg is %s" % (arg))


def t2(arg):
    print("my arg is %s" % (arg))


x = "me"
t = threading.Thread(target=t1, args=(x,))
t.start()

y = "you"
tx = threading.Thread(target=t2, args=(y,))
tx.start()
