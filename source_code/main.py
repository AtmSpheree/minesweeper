# -*- coding: utf-8 -*-

import sys
import traceback
from random import sample
from ui_design import Ui_MainWindow
from PyQt5.QtCore import QSize, QTimer
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel
from global_variables import MAIN_SIZES, MAIN_PATHS, FIELD_MODES, GAME_MODES


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
        self.setMouseTracking(True)
        self.all_cells = []
        self.label_time = QLabel('Время: 00:00')
        self.label_time.setStyleSheet('QLabel {font-size: 15px}')
        self.statusbar.addWidget(self.label_time)
        self.timer = QTimer()
        self.timer.timeout.connect(self.change_time)
        self.current_time = 0
        self.app_icon.setPixmap(QPixmap('favicon.png'))
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


def excepthook(exc_type, exc_value, exc_tb):
    print("".join(traceback.format_exception(exc_type, exc_value, exc_tb)))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.setWindowIcon(QIcon('favicon.png'))
    main_window.show()
    sys.excepthook = excepthook
    sys.exit(app.exec())
