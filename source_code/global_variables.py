import sqlite3


DB_CONNECTION = sqlite3.connect('main_database.db')


GAME_MODES = {'0': 'random',
              '1': 'safety'}
MAIN_SIZES = dict()
MAIN_PATHS = dict()
FIELD_MODES = dict()
cur = DB_CONNECTION.cursor()
req = cur.execute('''SELECT * FROM management_paths''').fetchall()
for i in req:
    MAIN_PATHS[i[1]] = i[2]
req = cur.execute('''SELECT * FROM cell_paths''').fetchall()
for i in req:
    MAIN_PATHS[i[1]] = i[2]
req = cur.execute('''SELECT * FROM field_modes''').fetchall()
for i in req:
    FIELD_MODES[str(i[0])] = ((i[1], i[2]), i[3])
req = cur.execute('''SELECT * FROM sizes''').fetchall()
for i in req:
    MAIN_SIZES[i[1]] = (i[2], i[3])