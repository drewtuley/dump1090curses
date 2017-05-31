import ConfigParser
import json
import sqlite3

from flask import Flask
from flask import request


class RegServer(Flask):
    db_filename = None

    def set_db(self, filename):
        self.db_filename = filename


app = RegServer(__name__)


@app.route('/search', methods=['GET'])
def search():
    search_icao_code = request.args.get('icao_code', '')
    app.logger.info('search for {}'.format(search_icao_code))
    sql = 'select registration from registration where icao_code = "{}";'.format(search_icao_code)
    app.logger.debug('sql = {}'.format(sql))
    ret = {}
    with sqlite3.connect(app.db_filename) as conn:
        cursor = conn.execute(sql)
        for row in cursor.fetchall():
            reg, = row
            app.logger.debug('reg={}'.format(reg))
            ret = {'registration': reg}
    return json.dumps(ret)


@app.route('/update', methods=['POST'])
def update():
    return json.dumps({'dd': 1213})


if __name__ == '__main__':
    config = ConfigParser.SafeConfigParser()
    config.read('dump1090curses.props')

    db_filename = config.get('directories', 'data') + '/' + config.get('database', 'dbname')
    app.set_db(db_filename)
    app.run(debug=True)
