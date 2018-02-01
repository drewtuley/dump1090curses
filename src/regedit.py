import ConfigParser
import curses
import curses.ascii
import logging
import sqlite3
from datetime import datetime
import sys


class OptionEdit(object):
    def __init__(self):
        self.type = None

    def setData(self, dataObject):
        self.dataObject = dataObject

    def getData(self):
        return self.dataObject


class Option(object):
    def __init__(self, value, visible, selected=False):
        self.value = value
        self.visible = visible
        self.selected = selected


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
    def __init__(self, row, col, text='', visible=True, **kwargs):
        self.row = row
        self.col = col
        self.text = text
        self.visible = visible
        if 'name' in kwargs:
            self.name = kwargs['name']
        else:
            self.name = None

        if 'post' in kwargs:
            self.postfunc = kwargs['post']
        else:
            self.postfunc = None

    def draw(self, win, color):
        text = '{text}'.format(text=self.text)
        win.addstr(self.row, self.col, text, color)

    def undraw(self, win):
        win.addstr(self.row, self.col, ' ' * len(self.text))

    def isvisible(self):
        return self.visible

    def setvisible(self, visible):
        self.visible = visible

    def update(self):
        return None


class EditBox(LabelBox):
    def __init__(self, row, col, visible=True, maxwidth=0, editType=OptionEdit(), **kwargs):
        super(EditBox, self).__init__(row, col, None, visible, **kwargs)
        self.maxwidth = maxwidth
        self.editType = editType

        if 'data' in kwargs:
            self.data = kwargs['data']
        else:
            self.data = None
        if 'datakey' in kwargs:
            self.datakey = kwargs['datakey']
        else:
            self.datakey = None

    def draw(self, win, color):
        text = self.data[self.datakey]
        val = '[{text:{width}s}]'.format(text=text, width=self.maxwidth)
        win.addstr(self.row, self.col, val, color)

    def undraw(self, win):
        win.addstr(self.row, self.col, ' ' * (self.maxwidth + 2))

    def set_focus(self, win, color):
        curses.curs_set(1)
        text = self.data[self.datakey]
        win.move(self.row, self.col + len(text) + 1)

    def edit(self, ch):
        if ch in [curses.KEY_RIGHT, curses.KEY_DOWN, 9, 10]:
            return FWD
        elif ch == curses.KEY_LEFT or ch == curses.KEY_UP:
            return REV
        text = self.data[self.datakey]
        logging.debug('preedit {}'.format(text))
        if ch == curses.KEY_BACKSPACE and len(text) > 0:
            text = text[:-1]
        elif self.editType.valid(ch) and len(text) < self.maxwidth:
            text = text + self.editType.transform(ch)
        self.data[self.datakey] = text
        logging.debug('postedit {}'.format(text))
        return ACTION

    def getData(self):
        return self.data

    def update(self):
        value = self.data[self.datakey]
        logging.debug('Update {} using {}'.format(self, value))
        return None


class OptionBox(LabelBox):
    def __init__(self, row, col, visible=True, maxwidth=0, editType=TextEdit(), **kwargs):
        super(OptionBox, self).__init__(row, col, None, visible, **kwargs)
        self.editType = editType
        self.optionList = kwargs['options']

        self.data = kwargs['data']

        self.selected_option = None
        idx = 0
        self.maxwidth = 1
        for opt in self.optionList:
            if opt.selected and self.selected_option is None:
                self.selected_option = idx
            idx += 1
            self.maxwidth += len(opt.value) + 1
        if self.selected_option is None:
            self.selection_option = 0
            self.optionList[0].selected = True

    def draw(self, win, color):
        win.addstr(self.row, self.col - (self.maxwidth + 2), ' ' * (self.maxwidth + 2))
        self.do_draw(win, color, False)

    def undraw(self, win):
        logging.debug('undraw: {} chrs'.format(self.maxwidth + 2))
        win.addstr(self.row, self.col, ' ' * (self.maxwidth + 2))

    def do_draw(self, win, color, with_focus):
        width = 1
        for option in self.optionList:
            if option.visible:
                width += len(option.value) + 1

        col = self.col - width
        win.addstr(self.row, col, '[', color)
        col += 1
        for option in self.optionList:
            if option.visible:
                actual_color = color
                if with_focus and option.selected:
                    actual_color |= curses.A_REVERSE
                win.addstr(self.row, col, option.value, actual_color)
                col += len(option.value)
                win.addstr(self.row, col, '/', color)
                col += 1
        win.addstr(self.row, col - 1, ']', color)

    def select_next_option(self, direction):
        found = False
        next_option = self.selected_option
        while not found:
            next_option += direction
            if next_option >= len(self.optionList):
                next_option = 0
            elif next_option < 0:
                next_option = len(self.optionList) - 1
            if self.optionList[next_option].visible:
                found = True

        self.optionList[self.selected_option].selected = False
        self.selected_option = next_option
        self.optionList[self.selected_option].selected = True

    def edit(self, ch):
        logging.info('In OptionBox edit')
        if ch == curses.KEY_RIGHT:
            self.select_next_option(FWD)
            return None
        elif ch == curses.KEY_LEFT:
            self.select_next_option(REV)
            return None
        elif ch == curses.KEY_UP:
            return REV
        elif ch == curses.KEY_DOWN:
            return FWD
        elif ch == 10:
            return ACTION

    def set_focus(self, win, color):
        self.do_draw(win, color, True)
        curses.curs_set(0)

    def get_selected_option(self):
        return self.optionList[self.selected_option]

    def getData(self):
        return self.data

    def set_selected_option(self, option_name):
        ix = 0
        for opt in self.optionList:
            if opt.value == option_name:
                opt.selected = True
                self.selected_option = ix
            else:
                opt.selected = False
            ix += 1

    def update(self):
        logging.debug('Update {} with {}'.format(self, self.data))
        if self.data['icaohex'] != '' and self.data['icaotype'] != '' and self.data['registration'] != '':
            if 'source' not in self.data or self.data['source'] == '':
                logging.debug('Enable Add')
                enable = ['Add']
                selopt = 'Add'
            else:
                logging.debug('Enable Update/Delete')
                enable = ['Update', 'Delete']
                selopt = 'Update'
            for opt in self.optionList:
                if opt.value in enable:
                    opt.visible = True

        else:
            ix = 0
            for opt in self.optionList:
                if opt.value not in ['Clear', 'Exit']:
                    opt.visible = False
                    opt.selected = False
                elif opt.value == 'Exit':
                    #self.selected_option = ix
                    opt.visible = True
                    opt.selected = True
                ix += 1


boxes = []
FWD = 1
REV = -1
EXIT = 255
ACTION = 100


def open_database(config, test):
    test_prefix = ''
    if test: test_prefix = 'test_'
    dbname = '{}/{}{}'.format(config.get('directories', 'data'), test_prefix, config.get('database', 'dbname'))
    logging.info('Opening db: ' + dbname)
    return sqlite3.connect(dbname)


def get_next_edit_idx(boxes, curpos, dir):
    pos = curpos + dir
    while True:
        if 0 <= pos < len(boxes):
            if (isinstance(boxes[pos], EditBox) or isinstance(boxes[pos], OptionBox)) and boxes[pos].isvisible():
                return pos
            else:
                pos += dir
        else:
            if pos < 0:
                pos = len(boxes) - 1
            else:
                pos = 0


def main(screen, test):
    curses.start_color()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    prev_state = curses.curs_set(0)

    curses.curs_set(1)

    screen.refresh()

    win = curses.newwin(curses.LINES, curses.COLS, 0, 0)
    win.bkgd(curses.color_pair(1))
    win.box()

    conn = open_database(config, test)

    focus_idx = get_next_edit_idx(boxes, -1, FWD)

    while True:
        # win.addstr(1,1,'{:4s}'.format(str(curses.LINES)), curses.color_pair(1))
        # win.addstr(2,1,'{:4s}'.format(str(curses.COLS)), curses.color_pair(1))

        logging.debug('Start update')
        for box in boxes:
            box.update()
            if not box.isvisible():
                box.undraw(win)
            if box.isvisible():
                box.draw(win, curses.color_pair(1))

        boxes[focus_idx].set_focus(win, curses.color_pair(1))

        win.refresh()
        ch = screen.getch()
        if ch == 27:
            break
        move_dir = boxes[focus_idx].edit(ch)
        if move_dir in [FWD, REV]:
            focus_idx = get_next_edit_idx(boxes, focus_idx, move_dir)
        elif move_dir == ACTION and boxes[focus_idx].postfunc is not None:
            move_dir = boxes[focus_idx].postfunc(boxes[focus_idx], conn)
            if move_dir is not None:
                if move_dir == EXIT:
                    break
                else:
                    focus_idx = get_next_edit_idx(boxes, focus_idx, move_dir)

    curses.curs_set(prev_state)


def after_reg(obj, conn):
    logging.debug('AfterReg called with {}'.format(obj))
    icaohex = obj.data['icaohex']
    reg = obj.data[obj.datakey]
    # dont lookup via reg if ICAOhex is set
    if len(reg) > 4 and len(icaohex) < 6:
        logging.debug('Access to db @ {}'.format(conn))
        sql = 'SELECT icao_code, equip FROM registration WHERE registration ="' + reg + '"'
        logging.debug('lookup {} using {}'.format(reg, sql))
        cursor = conn.cursor()
        cursor.execute(sql)

        for row in cursor.fetchall():
            icao_code, equip = row
            logging.debug('found icao:{} type: {}'.format(icao_code, equip))
            data = obj.getData()
            data['registration'] = reg
            data['icaohex'] = icao_code
            data['icaotype'] = equip
            data['source'] = 'registration'
            logging.debug('Data is now: {}'.format(data))

    if len(reg) == obj.maxwidth:
        return FWD
    return None


def after_hex(obj, conn):
    logging.debug('AfterHex called with {}'.format(obj))
    hex = obj.data[obj.datakey]
    if len(hex) == 6:
        logging.debug('Access to db @ {}'.format(conn))
        sql = 'SELECT registration, equip FROM registration WHERE icao_code ="' + hex + '"'
        logging.debug('lookup {} using {}'.format(hex, sql))
        cursor = conn.cursor()
        cursor.execute(sql)

        registration, equip = None, None
        for row in cursor.fetchall():
            registration, equip = row
            logging.debug('found reg:{} type: {}'.format(registration, equip))

        data = obj.getData()
        logging.debug('Data is {}'.format(data))
        if registration is not None:
            data['icaohex'] = hex
            data['icaotype'] = equip
            data['registration'] = registration
            data['source'] = 'icaohex'
            logging.debug('Data is now: {}'.format(data))
        else:
            data['icaotype'] = ''
            data['registration'] = ''
            if 'source' in data: del data['source']

        return FWD

    return None


def after_type(obj, conn):
    logging.debug('AfterType called with {}'.format(obj))

    icaotype = obj.data[obj.datakey]
    if len(icaotype) == obj.maxwidth: return FWD

    return None


def clear_data(data):
    data['icaohex'] = ''
    data['icaotype'] = ''
    data['registration'] = ''
    if 'source' in data: del data['source']


def after_option(obj, conn):
    logging.debug('After Option called with {}'.format(obj))

    selected = obj.get_selected_option()
    logging.debug('selected {}:'.format(selected.value))
    data = obj.getData()
    if selected.value == 'Exit':
        return EXIT
    elif selected.value == 'Clear':
        logging.debug('Data is {}'.format(data))
        clear_data(data)
        logging.debug('Data is now: {}'.format(data))
    elif selected.value in ['Update', 'Add', 'Delete']:
        logging.debug('Update/Add')
        dt = str(datetime.now())
        if selected.value == 'Add':
            sql = 'INSERT INTO registration (icao_code, registration, equip, created) SELECT "{icao_code}","{registration}","{equip}","{dt}";'
        elif selected.value == 'Update':
            if data['source'] == 'registration':
                sql = 'UPDATE registration SET icao_code="{icao_code}", equip="{equip}" WHERE registration="{registration}";'
            else:
                sql = 'UPDATE registration SET registration="{registration}", equip="{equip}" WHERE icao_code="{icao_code}";'
        else:
            sql = 'DELETE FROM registration WHERE icao_code="{icao_code}";'

        actual_sql = sql.format(icao_code=data['icaohex'], equip=data['icaotype'], registration=data['registration'], dt=dt)
        logging.debug('act sql: {}'.format(actual_sql))

        upd = conn.execute(actual_sql)
        conn.commit()
        logging.debug('update result=' + str(upd.description))
        clear_data(data)

    return FWD


def init():
    data_object = {'icaohex': '', 'icaotype': '', 'registration': ''}

    boxes.append(LabelBox(1, 7, 'Registration Editor', True))
    boxes.append(LabelBox(2, 7, '============ ======', True))

    boxes.append(LabelBox(4, 3, 'ICAO Hex:', True))
    boxes.append(EditBox(4, 25, True, 6, HexEdit(), data=data_object, datakey='icaohex', name='ICAOHEX', post=after_hex))

    boxes.append(LabelBox(6, 3, 'ICAO Type:', True))
    boxes.append(
        EditBox(6, 26, True, 5, AlphaNumUpper(), data=data_object, datakey='icaotype', name='ICAOTYPE', post=after_type))

    boxes.append(LabelBox(8, 3, 'Registration:', True))
    boxes.append(
        EditBox(8, 22, True, 9, RegEdit(), data=data_object, datakey='registration', name='REG', post=after_reg))

    boxes.append(OptionBox(10, 33, True, -1, OptionEdit(), data=data_object, name='OPTIONS',
                           options=[Option('Update', False), Option('Add', False), Option('Delete', False),
                                    Option('Clear', True ), Option('Exit', True, True)], post=after_option))

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
    test = False
    if len(sys.argv) == 2 and sys.argv[1] == '-t':
        test = True
        logging.debug('in test mode')

    init()

    if len(boxes) > 0:
        try:
            curses.wrapper(main, test)
        except Exception as ex:
            print(ex)
            logging.error(ex)
            exit(1)
    logging.info('stop')
