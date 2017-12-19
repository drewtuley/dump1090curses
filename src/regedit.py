import ConfigParser
import curses
import curses.ascii
import logging
import sqlite3
from datetime import datetime


class TextEdit(object):
    def __init__(self, validfunc=curses.ascii.isascii):
        self.validfunc = validfunc

    def valid(self, ch):
        return self.validfunc(ch)

    def transform(self, ch):
        return chr(ch)


class AlphaNumUpper(TextEdit):
    def __init__(self):
        super(AlphaNumUpper, self).__init__(curses.ascii.isalnum)

    def transform(self, ch):
        return chr(ch).upper()


class RegEdit(TextEdit):
    def __init__(self):
        super(RegEdit, self).__init__(lambda ch: curses.ascii.isalpha(ch) or curses.ascii.isdigit(ch) or ch == ord('-'))

    def transform(self, ch):
        return chr(ch).upper()


class YNEdit(TextEdit):
    def __init__(self):
        super(YNEdit, self).__init__(
            lambda ch: curses.ascii.isalpha(ch) and (chr(ch).upper() == 'Y' or chr(ch).upper() == 'N'))

    def transform(self, ch):
        return chr(ch).upper()


class HexEdit(TextEdit):
    def __init__(self):
        super(HexEdit, self).__init__(curses.ascii.isxdigit)

    def transform(self, ch):
        return chr(ch).upper()


class LabelBox(object):
    def __init__(self, row, col, value='', visible=True, **kwargs):
        self.row = row
        self.col = col
        self.value = value
        self.visible = visible
        if 'name' in kwargs:
            self.name = kwargs['name']
        else:
            self.name = None

        if 'post' in kwargs:
            self.postfunc = kwargs['post']
        else:
            self.postfunc = None

        self.custom = None

    def draw(self, win, color):
        val = '{value}'.format(value=self.value)
        win.addstr(self.row, self.col, val, color)

    def undraw(self, win):
        win.addstr(self.row, self.col, ' ' * len(self.value))

    def isvisible(self):
        return self.visible

    def setvisible(self, visible):
        self.visible = visible

    def setcustom(self, custom):
        logging.debug('setting custom value to {}'.format(custom))
        self.custom = custom

    def getcustom(self):
        return self.custom


class EditBox(LabelBox):
    def __init__(self, row, col, value='', visible=True, maxwidth=0, editType=TextEdit(), **kwargs):
        super(EditBox, self).__init__(row, col, value, visible, **kwargs)
        self.maxwidth = maxwidth
        self.editType = editType

    def draw(self, win, color):
        val = '[{value:{width}s}]'.format(value=self.value, width=self.maxwidth)
        win.addstr(self.row, self.col, val, color)

    def undraw(self, win):
        win.addstr(self.row, self.col, ' ' * (self.maxwidth + 2))

    def set_focus(self, win):
        win.move(self.row, self.col + len(self.value) + 1)

    def edit(self, ch):
        if ch == curses.KEY_BACKSPACE and len(self.value) > 0:
            self.value = self.value[:-1]
        elif self.editType.valid(ch) and len(self.value) < self.maxwidth:
            self.value = self.value + self.editType.transform(ch)


boxes = []


def open_database(config):
    dbname = config.get('directories', 'data') + '/' + config.get('database', 'dbname')
    logging.info('Opening db ' + dbname)
    return sqlite3.connect(dbname)


def get_next_edit_idx(boxes, curpos, dir):
    pos = curpos + dir
    while True:
        if 0 <= pos < len(boxes):
            if isinstance(boxes[pos], EditBox) and boxes[pos].isvisible():
                return pos
            else:
                pos += dir
        else:
            if pos < 0:
                pos = len(boxes) - 1
            else:
                pos = 0


def find_next_edit(boxes, curpos):
    pos = curpos + 1
    while True:
        if pos < len(boxes):
            if isinstance(boxes[pos], EditBox) and boxes[pos].isvisible():
                return pos
            else:
                pos += 1
        else:
            pos = 0


def find_prev_edit(boxes, curpos):
    pos = curpos - 1
    while True:
        if pos >= 0:
            if isinstance(boxes[pos], EditBox) and boxes[pos].isvisible():
                return pos
            else:
                pos -= 1
        else:
            pos = len(boxes) - 1


def main(screen):
    curses.start_color()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    prev_state = curses.curs_set(0)

    curses.curs_set(1)

    screen.refresh()

    win = curses.newwin(32, 155, 0, 0)
    win.bkgd(curses.color_pair(1))
    win.box()

    conn = open_database(config)

    focus_idx = find_next_edit(boxes, -1)
    ch = 0
    while True:
        # win.addstr(1,1,'{:4s}'.format(str(ch)), curses.color_pair(1))

        for box in boxes:
            if not box.isvisible():
                box.undraw(win)

        for box in boxes:
            if box.isvisible():
                box.draw(win, curses.color_pair(1))

        boxes[focus_idx].set_focus(win)

        win.refresh()
        ch = screen.getch()
        if ch == 27:
            break
        if ch in [curses.KEY_RIGHT, curses.KEY_DOWN, 9, 10]:
            focus_idx = find_next_edit(boxes, focus_idx)
        elif ch == curses.KEY_LEFT or ch == curses.KEY_UP:
            focus_idx = find_prev_edit(boxes, focus_idx)
        else:
            boxes[focus_idx].edit(ch)
            if boxes[focus_idx].postfunc is not None:
                boxes[focus_idx].postfunc(boxes[focus_idx], conn)

    curses.curs_set(prev_state)


def set_visibility(state, lst):
    for b in boxes:
        if b.name is not None and b.name in lst:
            b.setvisible(state)


def find_box(name):
    for b in boxes:
        if b.name is not None and b.name == name:
            return b

    return None


def set_values(box_hash):
    for key in box_hash:
        box = find_box(key)
        if box is not None:
            box.value = box_hash[key]


def get_values(box_list):
    rethash = {}
    for key in box_list:
        box = find_box(key)
        if box is not None:
            rethash[key] = box.value

    return rethash


def set_custom(name, custom):
    box = find_box(name)
    if box is not None:
        box.setcustom(custom)


def get_custom(name):
    box = find_box(name)
    if box is not None:
        return box.getcustom()


def after_reg(obj, conn):
    logging.debug('AfterReg called with {}'.format(obj))
    custom = get_custom('YN')
    if custom is not None and custom[1] != 'REG':
        logging.debug('Free edit cos icaohex update')
        return

    if len(obj.value) > 4:
        logging.debug('Access to db @ {}'.format(conn))
        sql = 'select icao_code, equip from registration where registration ="' + obj.value + '"'
        logging.debug('lookup {} using {}'.format(obj.value, sql))
        cursor = conn.cursor()
        cursor.execute(sql)

        icao_code, equip = None, None
        for row in cursor.fetchall():
            icao_code, equip = row
            logging.debug('found icao:{} type: {}'.format(icao_code, equip))

        if icao_code is None:
            set_visibility(True, ['ADD', 'YN'])
            set_custom('YN', ('ADD', 'REG'))
            set_values({'ICAOHEX': '', 'ICAOTYPE': ''})
        else:
            set_visibility(True, ['UPDATE', 'YN'])
            set_custom('YN', ('UPDATE', 'REG'))
            set_values({'ICAOHEX': icao_code, 'ICAOTYPE': equip})


def after_hex(obj, conn):
    logging.debug('AfterHex called with {}'.format(obj))
    custom = get_custom('YN')
    if custom is not None and custom[1] != 'ICAOHEX':
        logging.debug('Free edit cos reg update')
        return

    if len(obj.value) == 6:
        logging.debug('Access to db @ {}'.format(conn))
        sql = 'select registration, equip from registration where icao_code ="' + obj.value + '"'
        logging.debug('lookup {} using {}'.format(obj.value, sql))
        cursor = conn.cursor()
        cursor.execute(sql)

        registration, equip = None, None
        for row in cursor.fetchall():
            registration, equip = row
            logging.debug('found reg:{} type: {}'.format(registration, equip))

        if registration is None:
            set_visibility(True, ['ADD', 'YN'])
            set_custom('YN', ('ADD', 'ICAOHEX'))
            set_values({'REG': '', 'ICAOTYPE': '', 'YN': ''})
        else:
            set_visibility(True, ['UPDATE', 'YN'])
            set_custom('YN', ('UPDATE', 'ICAOHEX'))
            set_values({'REG': registration, 'ICAOTYPE': equip, 'YN': ''})

    else:
        logging.debug('set invisible')
        set_visibility(False, ['ADD', 'UPDATE', 'YN'])
        set_values({'REG': '', 'ICAOTYPE': '', 'YN': ''})


def after_yn(obj, conn):
    logging.debug('AfterReg called with {}'.format(obj))
    if obj.value == 'Y':
        if obj.custom is not None:
            mode = obj.custom
            logging.debug('{} db using {}'.format(mode[0], mode[1]))
            if mode[0] == 'ADD':
                sql = 'insert into registration (icao_code, registration, equip) select "{icao_code}","{registration}","{equip}";'
            else:
                if mode[1] == 'REG':
                    sql = 'update registration set icao_code="{icao_code}", equip="{equip}" where registration="{registration}";'
                else:
                    sql = 'update registration set registration="{registration}", equip="{equip}" where icao_code="{icao_code}";'
            values = get_values(['REG', 'ICAOTYPE', 'ICAOHEX'])
            logging.debug('values = {}'.format(values))
            real_sql = sql.format(icao_code=values['ICAOHEX'], registration=values['REG'], equip=values['ICAOTYPE'])
            logging.debug('SQL = {}'.format(real_sql))

            upd = conn.execute(real_sql)
            conn.commit()
            logging.debug('update result=' + str(upd.description))


    else:
        logging.debug('abort')

    set_values({'ICAOHEX': '', 'REG': '', 'ICAOTYPE': '', 'YN': ''})
    obj.setcustom(None)


def init():
    boxes.append(LabelBox(1, 7, 'Registration Editor', True))
    boxes.append(LabelBox(2, 7, '============ ======', True))

    boxes.append(LabelBox(4, 3, 'ICAO Hex:', True))
    boxes.append(EditBox(4, 24, '', True, 6, HexEdit(), name='ICAOHEX', post=after_hex))

    boxes.append(LabelBox(6, 3, 'ICAO Type:', True))
    boxes.append(EditBox(6, 25, '', True, 5, AlphaNumUpper(), name='ICAOTYPE'))

    boxes.append(LabelBox(8, 3, 'Registration:', True))
    boxes.append(EditBox(8, 21, '', True, 9, RegEdit(), name='REG', post=after_reg))

    boxes.append(LabelBox(11, 15, 'Add: (Y/N)', False, name='ADD'))
    boxes.append(LabelBox(11, 15, 'Update: (Y/N)', False, name='UPDATE'))
    boxes.append(EditBox(11, 29, '', False, 1, YNEdit(), name='YN', post=after_yn))

    logging.debug(boxes)


if __name__ == '__main__':
    config = ConfigParser.SafeConfigParser()
    config.read('dump1090curses.props')

    dt = str(datetime.now())[:10]
    logging.basicConfig(format='%(asctime)s %(message)s',
                        filename=config.get('directories', 'log') + '/regedit_' + dt + '.log',
                        level=logging.DEBUG)
    logging.captureWarnings(True)

    logging.debug('start')
    init()

    if len(boxes) > 0:
        try:
            curses.wrapper(main)
        except Exception as ex:
            print(ex)
            logging.error(ex)
            exit(1)
    logging.info('stop')
