# -*- coding: utf-8 -*-
import os.path
import sys
import traceback
from random import sample
from ui_design import Ui_MainWindow
from ui_db import Ui_Form
import ui_path_add
import ui_path_change
import ui_size_add
import ui_mode_add
import ui_size_change
import ui_mode_change
from PyQt5.QtCore import QSize, QTimer
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, \
                            QTableWidgetItem, QAction, QWidget
from global_variables import MAIN_SIZES, MAIN_PATHS, FIELD_MODES, GAME_MODES
import sqlite3


DB_CONNECTION = sqlite3.connect('main_database.db')


def mines_count(field, coords):
    y, x = coords
    result = 0
    for i in (y - 1, y, y + 1):
        for k in (x - 1, x, x + 1):
            if i < 0 or k < 0 or i >= len(field) or k >= len(field[0]):
                continue
            if field[i][k] == '.':
                result += 1
    if result == 0:
        return ' '
    return str(result)


def get_near_opened_cells(field, y, x, test):
    res = [f'{y} {x}']
    for i in (y - 1, y, y + 1):
        for k in (x - 1, x, x + 1):
            if i >= len(field) or i < 0 or k < 0 or k >= len(field[0]):
                continue
            if (i, k) == (y, x):
                continue
            if field[i][k][1]:
                continue
            if f'{i} {k}' in test:
                continue
            else:
                res.append(f'{i} {k}')
                if field[i][k][0] == ' ':
                    res += get_near_opened_cells(field, i, k, test + res)
                    res = list(set(res))
    return res


class MineSweeperField:
    def __init__(self, size, mines_count, mode='random'):
        self.size_x, self.size_y = size
        self.mines_count = mines_count
        self.mode = mode
        self.flags_coords = []
        self.create_field()

    def create_field(self):
        self.game_over = 0
        self.is_opened = False
        self.flags_coords = []
        self.mines_coords = []
        self.field = [[' ' for k in range(self.size_x)]
                      for i in range(self.size_y)]

    def set_mines(self, safety=None):
        positions = [(i, k) for i in range(self.size_y) for k in range(self.size_x)]
        if safety is not None:
            positions.remove(safety)
        for i, k in sample(positions, self.mines_count):
            self.mines_coords.append((i, k))
            self.field[i][k] = '.'
        for i, a in enumerate(self.field, 0):
            for k, b in enumerate(a, 0):
                if b == ' ':
                    self.field[i][k] = mines_count(self.field, (i, k))
        for i, a in enumerate(self.field, 0):
            for k, b in enumerate(a, 0):
                self.field[i][k] = (b, False)

    def open_cell(self, coords):
        if self.game_over != 0:
            return 0
        y, x = coords
        if not self.is_opened:
            if self.mode == 'safety':
                self.set_mines(coords)
            else:
                self.set_mines()
            self.is_opened = True
        if self.field[y][x][1]:
            return 0
        else:
            all_cells = []
            if self.field[y][x][0] == '.':
                self.game_over = 2
                all_cells = self.mines_coords
                self.change_lose_field(coords)
            elif self.field[y][x][0].isdigit():
                self.field[y][x] = (self.field[y][x][0], True)
                all_cells = [(y, x)]
                self.is_game_over()
            else:
                for a in get_near_opened_cells(self.field, y, x, []):
                    i, k = (int(a.split()[0]), int(a.split()[1]))
                    if (i, k) in self.flags_coords:
                        continue
                    self.field[i][k] = (self.field[i][k][0], True)
                    all_cells.append((i, k))
                self.is_game_over()
            if self.game_over == 1:
                all_cells += self.mines_coords
                self.change_win_field()
            return all_cells

    def change_lose_field(self, coords):
        for i, a in enumerate(self.field, 0):
            for k, b in enumerate(a, 0):
                if (i, k) in self.flags_coords:
                    if b[0] != '.':
                        self.field[i][k] = ('-', True)
                if b[0] == '.':
                    if (i, k) == coords:
                        self.field[i][k] = (',', True)
                    else:
                        self.field[i][k] = ('.', True)

    def change_win_field(self):
        for i, a in enumerate(self.field, 0):
            for k, b in enumerate(a, 0):
                if b[0] == '.':
                    self.add_flag((i, k))
        self.flags_coords = list(set(self.flags_coords))

    def is_game_over(self):
        for i in self.field:
            for k in i:
                if k[0] == '.' and not k[1]:
                    continue
                elif k[0] != '.' and k[1]:
                    continue
                return 0
        self.game_over = 1

    def __iter__(self):
        return iter(self.field)

    def get_game_value(self):
        return self.game_over

    def add_flag(self, coords):
        if coords not in self.flags_coords:
            self.flags_coords.append(coords)

    def delete_flag(self, coords):
        if coords in self.flags_coords:
            self.flags_coords.remove(coords)

    def get_flags_data(self):
        return self.flags_coords

    def get_cell(self, coords):
        return self.field[coords[0]][coords[1]]


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.load_start_interface()

    def load_start_interface(self):
        self.db_menu = self.menubar.addMenu('Menu')
        self.open_db_action = QAction(QIcon(MAIN_PATHS['file_icon']),
                                      '&Change DB...', self)
        self.db_menu.addAction(self.open_db_action)
        self.open_db_action.triggered.connect(self.change_db)
        self.setMouseTracking(True)
        self.all_cells = []
        self.label_time = QLabel('Время: 00:00')
        self.label_time.setStyleSheet('QLabel {font-size: 15px}')
        self.statusbar.addWidget(self.label_time)
        self.timer = QTimer()
        self.timer.timeout.connect(self.change_time)
        self.current_time = 0
        self.app_icon.setPixmap(QPixmap(MAIN_PATHS['main_icon']))
        self.mines_field = MineSweeperField((9, 9), 10, 'random')
        self.current_count_mines = 10
        self.lcd_count_mines.display(self.current_count_mines)
        self.gridLayout_field.setVerticalSpacing(3)
        self.gridLayout_field.setContentsMargins(0, 0, 0, 0)
        self.create_field()

        for_lcd = '''QLCDNumber {
                                 color: rgb(0, 0, 0);
                                 background-color: rgb(230, 230, 230);
                                 outline: none;
                     }'''
        self.lcd_count_mines.setStyleSheet(for_lcd)
        self.lcd_current_time.setStyleSheet(for_lcd)

        self.main_btns_group.buttonPressed.connect(self.btn_pressed_changer)
        self.main_btns_group.buttonReleased.connect(self.btn_released_changer)

    def change_db(self):
        self.db_window = DataBaseWidget()

    def change_time(self):
        self.current_time += 1
        if self.current_time <= 999:
            self.lcd_current_time.display(self.current_time)
            c = str(self.current_time % 60).rjust(2, '0')
            b = str(self.current_time // 60).rjust(2, '0')
            if self.current_time // 3600 != 0:
                a = f'{str(self.current_time // 3600).rjust(2, "0")}:'
            else:
                a = ''
            self.label_time.setText(f'Время: {a}{b}:{c}')

    def btn_pressed_changer(self, btn):
        btn.get_toggle_press()
        btn.change_btn()

    def btn_released_changer(self, btn):
        if btn.__class__.__name__ == 'ConditionButton':
            btn.change_condition()
            if btn.objectName() != 'switch_click_mode':
                a = FIELD_MODES[str(self.switch_field_mode.get_condition())]
                b = GAME_MODES[str(self.switch_game_mode.get_condition())]
                self.mines_field.__init__(*a, b)
                self.create_field()
        elif btn.__class__.__name__ == 'SmileButton':
            self.btn_smile.make_happy()
            self.btn_smile.get_toggle_press()
            self.btn_smile.change_btn()
            self.mines_field.create_field()
            self.create_field()
        btn.get_toggle_press()
        btn.change_btn()
        if btn.objectName() != 'switch_click_mode':
            a = FIELD_MODES[str(self.switch_field_mode.get_condition())]
            self.current_count_mines = a[1]
            self.lcd_count_mines.display(self.current_count_mines)
            self.current_time = 0
            self.lcd_current_time.display(self.current_time)
            self.label_time.setText('Время: 00:00')
            self.timer.stop()

    def create_field(self):
        while self.gridLayout_field.count() > 0:
            self.gridLayout_field.itemAt(0).widget().setParent(None)
        for i, a in enumerate(self.mines_field, 0):
            for k, b in enumerate(a, 0):
                cell = CellButton(self, (i, k))
                self.gridLayout_field.addWidget(cell, i, k)

    def update_field(self, data=None):
        if data is not None:
            data += self.mines_field.flags_coords
        if self.mines_field.get_game_value() != 0:
            self.timer.stop()
        if self.mines_field.get_game_value() == 1:
            self.btn_smile.make_win()
            self.btn_smile.change_btn()
        elif self.mines_field.get_game_value() == 2:
            self.btn_smile.make_died()
            self.btn_smile.change_btn()
        for i, a in enumerate(self.mines_field, 0):
            for k, b in enumerate(a, 0):
                if data is not None:
                    if (i, k) not in data:
                        continue
                if len(b) == 1:
                    temp = 'cell'
                    if (i, k) in self.mines_field.get_flags_data():
                        temp = 'flag'
                elif not b[1]:
                    temp = 'cell'
                    if (i, k) in self.mines_field.get_flags_data():
                        temp = 'flag'
                elif b[0] == ' ':
                    temp = 'cell_pressed'
                elif b[0].isdigit():
                    temp = f'cell_{b[0]}'
                else:
                    if self.mines_field.get_game_value() == 1:
                        temp = 'flag'
                    elif self.mines_field.get_game_value() == 2:
                        if b[0] == '.':
                            temp = 'mine_default'
                        elif b[0] == ',':
                            temp = 'mine_active'
                        elif b[0] == '-':
                            temp = 'mine_incorrect'
                self.gridLayout_field.itemAtPosition(i, k).widget().setIcon(QIcon(MAIN_PATHS[temp]))


class CellButton(QPushButton):
    def __init__(self, window, coords):
        super().__init__()
        self.setGeometry(0, 0, *MAIN_SIZES["cell_btn"])
        self.setIcon(QIcon(MAIN_PATHS['cell']))
        self.setIconSize(QSize(*MAIN_SIZES["cell_btn"]))
        self.setStyleSheet("QPushButton {border: none;}")
        self.window = window
        self.coords = coords

    def mouseReleaseEvent(self, event):
        if self.window.switch_click_mode.get_condition() == 0:
            a = Qt.RightButton
            b = Qt.LeftButton
        else:
            a = Qt.LeftButton
            b = Qt.RightButton
        if event.button() == b:
            self.window.btn_smile.make_happy()
            self.window.btn_smile.change_btn()
            self.window.update_field(self.window.all_cells)
            self.window.all_cells = []

    def mousePressEvent(self, event):
        while True:
            if self.window.mines_field.game_over != 0:
                break
            if self.window.switch_click_mode.get_condition() == 0:
                a = Qt.RightButton
                b = Qt.LeftButton
            else:
                a = Qt.LeftButton
                b = Qt.RightButton
            if event.button() == a:
                if self.coords in self.window.mines_field.get_flags_data():
                    self.window.mines_field.delete_flag((self.coords))
                    self.window.current_count_mines += 1
                else:
                    self.window.mines_field.add_flag((self.coords))
                    self.window.current_count_mines -= 1
                if self.window.lcd_count_mines.intValue() >= -99:
                    self.window.lcd_count_mines.display(self.window.current_count_mines)
                self.window.all_cells = [(self.coords)]
                self.window.update_field(self.window.all_cells)
                self.window.all_cells = []
            elif event.button() == b:
                if self.coords not in self.window.mines_field.get_flags_data():
                    self.window.btn_smile.make_surprised()
                    self.window.btn_smile.change_btn()
                    temp = False
                    if len(self.window.mines_field.get_cell(self.coords)) == 1:
                        temp = True
                    elif not self.window.mines_field.get_cell(self.coords)[1]:
                        temp = True
                    if temp:
                        self.setIcon(QIcon(MAIN_PATHS['cell_pressed']))
                        if not self.window.mines_field.is_opened:
                            self.window.timer.start(1000)
                        self.window.all_cells = self.window.mines_field.open_cell(self.coords)
            break


class DataBaseWidget(QWidget, Ui_Form):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.init_UI()

    def init_UI(self):
        self.setWindowIcon(QIcon(MAIN_PATHS['file_icon']))
        self.tabWidget.setTabText(0, 'Основные пути')
        self.tabWidget.setTabText(1, 'Пути клеток')
        self.tabWidget.setTabText(2, 'Размеры')
        self.tabWidget.setTabText(3, 'Режимы')
        self.btn_add_management_path.clicked.connect(self.add_management_path)
        self.btn_add_cell_path.clicked.connect(self.add_cell_path)
        self.btn_add_mode.clicked.connect(self.add_field_mode)
        self.btn_add_size.clicked.connect(self.add_size)
        self.btn_change_management_path.clicked.connect(self.change_management_path)
        self.btn_change_cell_path.clicked.connect(self.change_cell_path)
        self.btn_change_size.clicked.connect(self.change_size)
        self.btn_change_mode.clicked.connect(self.change_field_mode)
        self.btn_remove_management_path.clicked.connect(self.remove_management_path)
        self.btn_remove_cell_path.clicked.connect(self.remove_cell_path)
        self.btn_remove_size.clicked.connect(self.remove_size)
        self.btn_remove_mode.clicked.connect(self.remove_field_mode)
        self.render_db()
        self.show()

    def render_db(self):
        cur = DB_CONNECTION.cursor()
        data = cur.execute('''SELECT * FROM management_paths
                                      ORDER BY id DESC''').fetchall()
        header = ['ИД', 'Название', 'Путь']
        self.tableWidget_management_paths.setColumnCount(3)
        self.tableWidget_management_paths.setRowCount(0)
        self.tableWidget_management_paths.setHorizontalHeaderLabels(header)
        for i, row in enumerate(data):
            self.tableWidget_management_paths.setRowCount(
                self.tableWidget_management_paths.rowCount() + 1)
            for j, elem in enumerate(row):
                self.tableWidget_management_paths.setItem(
                    i, j, QTableWidgetItem(str(elem)))

        data = cur.execute('''SELECT * FROM cell_paths
                                      ORDER BY id DESC''').fetchall()
        header = ['ИД', 'Название', 'Путь']
        self.tableWidget_cell_paths.setColumnCount(3)
        self.tableWidget_cell_paths.setRowCount(0)
        self.tableWidget_cell_paths.setHorizontalHeaderLabels(header)
        for i, row in enumerate(data):
            self.tableWidget_cell_paths.setRowCount(
                self.tableWidget_cell_paths.rowCount() + 1)
            for j, elem in enumerate(row):
                self.tableWidget_cell_paths.setItem(
                    i, j, QTableWidgetItem(str(elem)))

        data = cur.execute('''SELECT * FROM sizes
                                      ORDER BY id DESC''').fetchall()
        header = ['ИД', 'Название', 'Ось X', 'Ось Y']
        self.tableWidget_sizes.setColumnCount(4)
        self.tableWidget_sizes.setRowCount(0)
        self.tableWidget_sizes.setHorizontalHeaderLabels(header)
        for i, row in enumerate(data):
            self.tableWidget_sizes.setRowCount(
                self.tableWidget_sizes.rowCount() + 1)
            for j, elem in enumerate(row):
                self.tableWidget_sizes.setItem(
                    i, j, QTableWidgetItem(str(elem)))

        data = cur.execute('''SELECT * FROM field_modes
                                      ORDER BY id DESC''').fetchall()
        header = ['ИД', 'Ось X', 'Ось Y', 'Количество мин']
        self.tableWidget_modes.setColumnCount(4)
        self.tableWidget_modes.setRowCount(0)
        self.tableWidget_modes.setHorizontalHeaderLabels(header)
        for i, row in enumerate(data):
            self.tableWidget_modes.setRowCount(
                self.tableWidget_modes.rowCount() + 1)
            for j, elem in enumerate(row):
                self.tableWidget_modes.setItem(
                    i, j, QTableWidgetItem(str(elem)))

        cur.close()

    def add_management_path(self):
        self.second_form = PathAddForm(self, 'management_paths')
        self.render_db()

    def change_management_path(self):
        if self.tableWidget_management_paths.currentRow() != -1:
            self.second_form = PathChangeForm(self, 'management_paths')
            self.label_error.setText('')
        else:
            self.label_error.setText('Выберите запись в таблице')
        self.render_db()

    def remove_management_path(self):
        if self.tableWidget_management_paths.currentRow() != -1:
            cur = DB_CONNECTION.cursor()
            id = int(self.tableWidget_management_paths.item(
                     self.tableWidget_management_paths.currentRow(), 0).text())
            cur.execute('''DELETE from management_paths WHERE id = ?''',
                        (id,))
            DB_CONNECTION.commit()
            self.label_error.setText('')
        else:
            self.label_error.setText('Выберите запись в таблице')
        self.render_db()

    def add_cell_path(self):
        self.second_form = PathAddForm(self, 'cell_paths')
        self.render_db()

    def change_cell_path(self):
        if self.tableWidget_cell_paths.currentRow() != -1:
            self.second_form = PathChangeForm(self, 'cell_paths')
            self.label_error.setText('')
        else:
            self.label_error.setText('Выберите запись в таблице')
        self.render_db()

    def remove_cell_path(self):
        if self.tableWidget_cell_paths.currentRow() != -1:
            cur = DB_CONNECTION.cursor()
            id = int(self.tableWidget_cell_paths.item(
                     self.tableWidget_cell_paths.currentRow(), 0).text())
            cur.execute('''DELETE from cell_paths WHERE id = ?''',
                        (id,))
            DB_CONNECTION.commit()
            self.label_error.setText('')
        else:
            self.label_error.setText('Выберите запись в таблице')
        self.render_db()

    def add_size(self):
        self.second_form = SizeAddForm(self)
        self.render_db()

    def change_size(self):
        if self.tableWidget_sizes.currentRow() != -1:
            self.second_form = SizeChangeForm(self)
            self.label_error.setText('')
        else:
            self.label_error.setText('Выберите запись в таблице')
        self.render_db()

    def remove_size(self):
        if self.tableWidget_sizes.currentRow() != -1:
            cur = DB_CONNECTION.cursor()
            id = int(self.tableWidget_sizes.item(
                self.tableWidget_sizes.currentRow(), 0).text())
            cur.execute('''DELETE from sizes WHERE id = ?''',
                        (id,))
            DB_CONNECTION.commit()
            self.label_error.setText('')
        else:
            self.label_error.setText('Выберите запись в таблице')
        self.render_db()

    def add_field_mode(self):
        self.second_form = ModeAddForm(self)
        self.render_db()

    def change_field_mode(self):
        if self.tableWidget_modes.currentRow() != -1:
            self.second_form = ModeChangeForm(self)
            self.label_error.setText('')
        else:
            self.label_error.setText('Выберите запись в таблице')
        self.render_db()

    def remove_field_mode(self):
        if self.tableWidget_modes.currentRow() != -1:
            cur = DB_CONNECTION.cursor()
            id = int(self.tableWidget_modes.item(
                     self.tableWidget_modes.currentRow(), 0).text())
            cur.execute('''DELETE from field_modes WHERE id = ?''',
                        (id,))
            DB_CONNECTION.commit()
            self.label_error.setText('')
        else:
            self.label_error.setText('Выберите запись в таблице')
        self.render_db()


class SizeChangeForm(QWidget, ui_size_change.Ui_Form):
    def __init__(self, *args):
        super().__init__()
        self.setupUi(self)
        self.initUI(*args)

    def initUI(self, *args):
        self.main_obj = args[0]
        self.current_row = self.main_obj.tableWidget_sizes.currentRow()
        self.btn_change.clicked.connect(self.change_item)
        data = self.main_obj.tableWidget_sizes.item(
                 self.main_obj.tableWidget_sizes.currentRow(), 1).text()
        self.le_short_name.setText(data)
        data = self.main_obj.tableWidget_sizes.item(
                 self.main_obj.tableWidget_sizes.currentRow(), 2).text()
        self.le_x_axis.setText(data)
        data = self.main_obj.tableWidget_sizes.item(
                 self.main_obj.tableWidget_sizes.currentRow(), 3).text()
        self.le_y_axis.setText(data)
        self.show()

    def change_item(self):
        cur = DB_CONNECTION.cursor()
        short_names = cur.execute(f'SELECT short_name FROM sizes').fetchall()
        name = self.le_short_name.text()
        if (not self.le_short_name.text() or not self.le_x_axis.text() or
           not self.le_y_axis.text()):
            self.set_error()
        elif (not self.le_x_axis.text().isdigit() or
              not self.le_y_axis.text().isdigit()):
            self.set_error()
        elif int(self.le_x_axis.text()) <= 0 or int(self.le_y_axis.text()) <= 0:
            self.set_error()
        elif name in [i[0] for i in short_names]:
            self.set_error()
        else:
            self.label_error.setText('')
            cur = DB_CONNECTION.cursor()
            try:
                id = self.main_obj.tableWidget_sizes.item(
                       self.current_row, 0).text()
                req = (f'''UPDATE sizes SET short_name = ?,
                           x_axis = ?, y_axis = ? WHERE id = ?''',
                       (self.le_short_name.text(), self.le_x_axis.text(),
                        self.le_y_axis.text(), id))
                cur.execute(*req)
                DB_CONNECTION.commit()
                self.close()
                self.main_obj.render_db()
            except Exception:
                pass

    def set_error(self):
        self.label_error.setText('Неверно заполнены поля')


class ModeChangeForm(QWidget, ui_mode_change.Ui_Form):
    def __init__(self, *args):
        super().__init__()
        self.setupUi(self)
        self.initUI(*args)

    def initUI(self, *args):
        self.main_obj = args[0]
        self.current_row = self.main_obj.tableWidget_modes.currentRow()
        self.btn_change.clicked.connect(self.change_item)
        data = self.main_obj.tableWidget_modes.item(
                 self.main_obj.tableWidget_modes.currentRow(), 1).text()
        self.le_x_axis.setText(data)
        data = self.main_obj.tableWidget_modes.item(
                 self.main_obj.tableWidget_modes.currentRow(), 2).text()
        self.le_y_axis.setText(data)
        data = self.main_obj.tableWidget_modes.item(
                 self.main_obj.tableWidget_modes.currentRow(), 3).text()
        self.le_mines_count.setText(data)
        self.show()

    def change_item(self):
        if (not self.le_x_axis.text() or not self.le_y_axis.text() or
                not self.le_mines_count.text()):
            self.set_error()
        elif (not self.le_x_axis.text().isdigit() or
              not self.le_y_axis.text().isdigit() or
              not self.le_mines_count.text().isdigit()):
            self.set_error()
        elif (int(self.le_x_axis.text()) <= 0 or int(self.le_y_axis.text()) <= 0 or
              int(self.le_mines_count.text()) <= 0):
            self.set_error()
        else:
            self.label_error.setText('')
            cur = DB_CONNECTION.cursor()
            try:
                id = self.main_obj.tableWidget_modes.item(
                       self.current_row, 0).text()
                req = (f'''UPDATE field_modes SET x_axis = ?, y_axis = ?,
                           mines_count = ? WHERE id = ?''',
                       (self.le_x_axis.text(), self.le_y_axis.text(),
                        self.le_mines_count.text(), id))
                cur.execute(*req)
                DB_CONNECTION.commit()
                self.close()
                self.main_obj.render_db()
            except Exception:
                pass

    def set_error(self):
        self.label_error.setText('Неверно заполнены поля')


class ModeAddForm(QWidget, ui_mode_add.Ui_Form):
    def __init__(self, *args):
        super().__init__()
        self.setupUi(self)
        self.initUI(*args)

    def initUI(self, *args):
        self.main_obj = args[0]
        self.btn_add.clicked.connect(self.add_item)
        self.show()

    def add_item(self):
        if (not self.le_x_axis.text() or not self.le_y_axis.text() or
           not self.le_mines_count.text()):
            self.set_error()
        elif (not self.le_x_axis.text().isdigit() or
              not self.le_y_axis.text().isdigit() or
              not self.le_mines_count.text().isdigit()):
            self.set_error()
        elif (int(self.le_x_axis.text()) <= 0 or int(self.le_y_axis.text()) <= 0 or
              int(self.le_mines_count.text()) <= 0):
            self.set_error()
        else:
            self.label_error.setText('')
            cur = DB_CONNECTION.cursor()
            try:
                req = (f'''INSERT INTO field_modes(x_axis, y_axis, mines_count)
                           VALUES(?, ?, ?)''',
                       (self.le_x_axis.text(), int(self.le_y_axis.text()),
                        int(self.le_mines_count.text())))
                cur.execute(*req)
                DB_CONNECTION.commit()
                self.close()
                self.main_obj.render_db()
            except Exception:
                pass

    def set_error(self):
        self.label_error.setText('Неверно заполнены поля')


class SizeAddForm(QWidget, ui_size_add.Ui_Form):
    def __init__(self, *args):
        super().__init__()
        self.setupUi(self)
        self.initUI(*args)

    def initUI(self, *args):
        self.main_obj = args[0]
        self.btn_add.clicked.connect(self.add_item)
        self.show()

    def add_item(self):
        cur = DB_CONNECTION.cursor()
        short_names = cur.execute(f'SELECT short_name FROM sizes').fetchall()
        name = self.le_short_name.text()
        if (not self.le_short_name.text() or not self.le_x_axis.text() or
           not self.le_y_axis.text()):
            self.set_error()
        elif (not self.le_x_axis.text().isdigit() or
              not self.le_y_axis.text().isdigit()):
            self.set_error()
        elif int(self.le_x_axis.text()) <= 0 or int(self.le_y_axis.text()) <= 0:
            self.set_error()
        elif name in [i[0] for i in short_names]:
            self.set_error()
        else:
            self.label_error.setText('')
            cur = DB_CONNECTION.cursor()
            try:
                req = (f'''INSERT INTO sizes(short_name, x_axis, y_axis)
                           VALUES(?, ?, ?)''',
                       (self.le_short_name.text(), int(self.le_x_axis.text()),
                        int(self.le_y_axis.text())))
                cur.execute(*req)
                DB_CONNECTION.commit()
                self.close()
                self.main_obj.render_db()
            except Exception:
                pass

    def set_error(self):
        self.label_error.setText('Неверно заполнены поля')


class PathAddForm(QWidget, ui_path_add.Ui_Form):
    def __init__(self, *args):
        super().__init__()
        self.setupUi(self)
        self.initUI(*args)

    def initUI(self, *args):
        self.main_obj = args[0]
        self.table_name = args[1]
        self.btn_add.clicked.connect(self.add_item)
        self.show()

    def add_item(self):
        cur = DB_CONNECTION.cursor()
        short_names = cur.execute(f'SELECT short_name FROM {self.table_name}').fetchall()
        name = self.le_short_name.text()
        if not self.le_short_name.text() or not self.le_path.text():
            self.set_error()
        if not os.path.exists(self.le_path.text()):
            self.set_error()
        elif not os.path.isfile(self.le_path.text()):
            self.set_error()
        elif not self.le_path.text().endswith('.png'):
            self.set_error()
        elif name in [i[0] for i in short_names]:
            self.set_error()
        else:
            self.label_error.setText('')
            cur = DB_CONNECTION.cursor()
            try:
                req = (f'''INSERT INTO {self.table_name}(short_name, path)
                           VALUES(?, ?)''',
                       (self.le_short_name.text(), self.le_path.text()))
                cur.execute(*req)
                DB_CONNECTION.commit()
                self.close()
                self.main_obj.render_db()
            except Exception:
                pass

    def set_error(self):
        self.label_error.setText('Неверно заполнены поля')


class PathChangeForm(QWidget, ui_path_change.Ui_Form):
    def __init__(self, *args):
        super().__init__()
        self.setupUi(self)
        self.initUI(*args)

    def initUI(self, *args):
        self.main_obj = args[0]
        self.table_name = args[1]
        exec(f'self.current_row = self.main_obj.tableWidget_{args[1]}.currentRow()')
        self.btn_change.clicked.connect(self.change_item)
        data = eval(f'self.main_obj.tableWidget_{args[1]}.item('
                    f'self.main_obj.tableWidget_{args[1]}.currentRow(), 1).text()')
        self.le_short_name.setText(data)
        data = eval(f'self.main_obj.tableWidget_{args[1]}.item('
                    f'self.main_obj.tableWidget_{args[1]}.currentRow(), 2).text()')
        self.le_path.setText(data)
        self.show()

    def change_item(self):
        if not self.le_short_name.text() or not self.le_path.text():
            self.set_error()
        if not os.path.exists(self.le_path.text()):
            self.set_error()
        elif not os.path.isfile(self.le_path.text()):
            self.set_error()
        elif not self.le_path.text().endswith('.png'):
            self.set_error()
        else:
            self.label_error.setText('')
            cur = DB_CONNECTION.cursor()
            try:
                id = eval(f'self.main_obj.tableWidget_{self.table_name}.item('
                          f'self.current_row, 0).text()')
                req = (f'''UPDATE {self.table_name} SET short_name = ?,
                           path = ? WHERE id = ?''',
                       (self.le_short_name.text(), self.le_path.text(), id))
                cur.execute(*req)
                DB_CONNECTION.commit()
                self.close()
                self.main_obj.render_db()
            except Exception as ex:
                pass

    def set_error(self):
        self.label_error.setText('Неверно заполнены поля')


def excepthook(exc_type, exc_value, exc_tb):
    print("".join(traceback.format_exception(exc_type, exc_value, exc_tb)))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.setWindowIcon(QIcon(MAIN_PATHS['main_icon']))
    main_window.show()
    sys.excepthook = excepthook
    sys.exit(app.exec())
