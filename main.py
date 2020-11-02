from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import Qt, QPoint, QThread, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QPixmap, QMovie
from PyQt5.QtWidgets import QApplication, QLabel, QSystemTrayIcon, QAction, QMenu, QWidget, QDesktopWidget
import sys
import random
import os
import webbrowser
import urllib.request, urllib.error
import json
import time
from screeninfo import get_monitors
import feedparser


# Get path for temp folder when the program is executed
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


# Thread for opening the web browser
# Only seems to be a problem in Linux
class OpenWeb(QThread):
    def __init__(self, function, *args, **kwargs):
        super(OpenWeb, self).__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs

    @pyqtSlot()
    def run(self):
        self.function(*self.args, **self.kwargs)


def open_about():
    webbrowser.open("https://modestcarl.itch.io/homestuck-desktop-buddies", 2)


def open_update(url):
    webbrowser.open(url, 2)


def open_hs():
    webbrowser.open("https://www.homestuck.com/", 2)


def open_hs2():
    webbrowser.open("https://www.homestuck2.com/", 2)


# Thread for checking for HS^2 updates
class Worker(QThread):
    updateSignal = pyqtSignal(bool)

    def __init__(self,  parent=None):
        QThread.__init__(self, parent)
        self.running = False

    @pyqtSlot()
    def run(self):
        self.running = True
        while self.running:
            self.check_for_update()
            time.sleep(30)  # Check for update every 30 seconds

    def stop(self):
        self.running = False
        self.terminate()

    def check_for_update(self):
        url = "https://www.homestuck2.com/story/rss"
        self.data_dict = {}
        try:
            feed = feedparser.parse(url)
            self.data_dict["last_update_date"] = feed.feed.updated

            if os.path.isfile(resource_path("data/last_update.json")):  # Check if last_update.json exists
                with open(resource_path("data/last_update.json"), "r") as last_update_file:  # Open it for reading
                    local_data = json.loads(last_update_file.read())  # Copy the content of the dict into another dict
                    if local_data["last_update_date"] != self.data_dict["last_update_date"]:
                        self.updateSignal.emit(True)  # If the dates of both dicts don't match, send the update signal
                # Write the relevant update data to the JSON file
                for index, entries in enumerate(feed.entries):
                    if entries.updated != self.data_dict["last_update_date"]:
                        self.data_dict["last_update_first_page"] = feed.entries[index - 1].title
                        self.data_dict["last_update_first_page_title"] = feed.entries[index - 1].description
                        self.data_dict["last_update_first_page_url"] = feed.entries[index - 1].link
                        self.data_dict["last_update_page_count"] = index
                        break
                with open(resource_path("data/last_update.json"), "w") as last_update_file:  # Open the JSON for writing
                    json.dump(self.data_dict, last_update_file)  # Write the new last update data to the local JSON
            else:
                with open(resource_path("data/last_update.json"), "w") as last_update_file:  # Open the JSON for writing
                    json.dump(self.data_dict, last_update_file)  # Write the new last update data to the local JSON

            # data_dict["last_update"] = feed.entries[0].title
        except urllib.error.HTTPError as e:
            print(e.code)
        except urllib.error.URLError as e:
            print(e.args)


class BuddySelection(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_ui()
        self.active_buddies = []  # Active buddies list to iterate through it to celebrate the update
        self.want_to_close = False  # Check for overriding the close event

        # Creating the system tray icon
        self.tray_icon = QSystemTrayIcon(self)

        # Action for reopening the main window
        open_action = QAction("Open", self)
        open_action.triggered.connect(self.show)

        # Action for opening the Homestuck website
        open_hs_action = QAction("Open Homestuck", self)
        open_hs_action.setIcon(QtGui.QIcon(resource_path('graphics/logo.ico')))
        open_hs_action.triggered.connect(self.open_hs)

        # Action for opening the Homestuck^2 website
        open_hs2_action = QAction("Open Homestuck^2", self)
        open_hs2_action.setIcon(QtGui.QIcon(resource_path('graphics/logo-hs2.ico')))
        open_hs2_action.triggered.connect(self.open_hs2)

        # Action for opening the software itch.io page
        about_action = QAction("About", self)
        about_action.triggered.connect(self.open_about)

        # Action for quiting
        quit_action = QAction("Exit", self)
        quit_action.triggered.connect(self.exit)

        # Creating the context menu for the system tray icon and adding the previously defined actions
        tray_menu = QMenu()
        tray_menu.addAction(open_action)
        tray_menu.addAction(open_hs_action)
        tray_menu.addAction(open_hs2_action)
        tray_menu.addAction(about_action)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)  # Adding the context menu to the tray icon

        self.tray_icon.setIcon(QtGui.QIcon(resource_path('graphics/logo.ico')))  # Setting the icon
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.show_hide)  # Connecting the click to the show function

        self.minimized_once = False  # Variable for checking if the window has been minimized to tray once

        # Creation of the thread to check for updates
        self.worker = Worker(self)
        self.worker.updateSignal.connect(self.celebrate_update)
        self.worker.start()

    def show_hide(self, reason):
        # If the system tray icon was clicked, and the main window is hidden, show the main window
        if reason == QSystemTrayIcon.Trigger:
            if self.isHidden():
                self.show()

    def celebrate_update(self):
        update_title = self.worker.data_dict["last_update_first_page_title"]

        # Format the update title
        update_title += "\n(" + str(self.worker.data_dict["last_update_page_count"]) + " pages long.)"

        self.tray_icon.showMessage("Homestuck^2 Update", update_title,
                                   QtGui.QIcon(resource_path("graphics/logo-hs2.ico")))
        self.tray_icon.messageClicked.connect(self.open_update)  # Open the new update

        # Loop through all active buddies and make them celebrate accordingly
        for buddy in self.active_buddies:
            buddy.celebrate_update()

    # Open the itch.io page for the project
    def open_about(self):
        self.opener = OpenWeb(open_about)
        self.opener.start()

    # Open the HS^2 website on the first page of the last update
    def open_update(self):
        self.opener = OpenWeb(open_update, self.worker.data_dict["last_update_first_page_url"])
        self.opener.start()
        self.tray_icon.messageClicked.disconnect()

    # Open the Homestuck website
    def open_hs(self):
        self.opener = OpenWeb(open_hs)
        self.opener.start()

    # Open the Homestuck^2 website
    def open_hs2(self):
        self.opener = OpenWeb(open_hs2)
        self.opener.start()

    def init_ui(self):
        # Set the window icon and title
        self.setWindowIcon(QtGui.QIcon(resource_path('graphics/logo.ico')))
        self.setWindowTitle("Homestuck Desktop Buddies v0.3.1")

        # Set window geometry and disable resizing
        self.setGeometry(0, 0, 850, 400)
        self.resize(850, 400)
        self.setMinimumSize(QtCore.QSize(850, 400))
        self.setMaximumSize(QtCore.QSize(850, 400))
        self.setStyleSheet("background-color: #c6c6c6;")

        # Center window
        qtRectangle = self.frameGeometry()
        centerPoint = QDesktopWidget().availableGeometry().center()
        qtRectangle.moveCenter(centerPoint)
        self.move(qtRectangle.topLeft())

        # Initialize the rest of the GUI
        self.grid_layout_widget = QtWidgets.QWidget(self)
        self.grid_layout_widget.setGeometry(QtCore.QRect(60, 0, 730, 400))
        self.grid_layout_widget.setObjectName("gridLayoutWidget")
        self.grid_layout = QtWidgets.QGridLayout(self.grid_layout_widget)
        self.grid_layout.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setHorizontalSpacing(6)
        self.grid_layout.setObjectName("gridLayout")

        self.frame = QtWidgets.QFrame(self.grid_layout_widget)
        self.frame.setStyleSheet("background-color: #efefef;")
        self.frame.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame.setObjectName("frame")
        self.frame.resize(730, 400)

        self.grid_layout_widget_2 = QtWidgets.QWidget(self.frame)
        self.grid_layout_widget_2.setGeometry(QtCore.QRect(9, 0, 711, 401))
        self.grid_layout_widget_2.setObjectName("gridLayoutWidget_2")
        self.grid_layout_2 = QtWidgets.QGridLayout(self.grid_layout_widget_2)
        self.grid_layout_2.setContentsMargins(0, 0, 0, 0)
        self.grid_layout_2.setObjectName("gridLayout_2")

        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(resource_path("graphics/menu/logo.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)

        self.john_button = QtWidgets.QPushButton(self.grid_layout_widget_2)
        self.john_button.setStyleSheet("QPushButton {\n"
                                      "    border: none;\n"
                                      "    background-color: #efefef;\n"
                                      "}\n"
                                      "\n"
                                      "QPushButton:checked{\n"
                                      "    border-top: 2px solid #535353;\n"
                                      "    border-left: 2px solid #535353;\n"
                                      "    background-color: #c6c6c6;\n"
                                      "}")
        self.john_button.setText("")
        john_icon = QtGui.QIcon()
        john_icon.addPixmap(QtGui.QPixmap(resource_path("graphics/menu/john-icon.png")), QtGui.QIcon.Normal,
                        QtGui.QIcon.Off)
        self.john_button.setIcon(john_icon)
        self.john_button.setIconSize(QtCore.QSize(160, 160))
        self.john_button.setCheckable(True)
        self.john_button.setChecked(False)
        self.john_button.setAutoRepeat(False)
        self.john_button.setFlat(True)
        self.john_button.setObjectName("johnButton")
        self.grid_layout_2.addWidget(self.john_button, 0, 0, 1, 1)

        self.rose_button = QtWidgets.QPushButton(self.grid_layout_widget_2)
        self.rose_button.setStyleSheet("QPushButton {\n"
                                       "    border: none;\n"
                                       "    background-color: #efefef;\n"
                                       "}\n"
                                       "\n"
                                       "QPushButton:checked{\n"
                                       "    border-top: 2px solid #535353;\n"
                                       "    border-left: 2px solid #535353;\n"
                                       "    background-color: #c6c6c6;\n"
                                       "}")
        self.rose_button.setText("")
        rose_icon = QtGui.QIcon()
        rose_icon.addPixmap(QtGui.QPixmap(resource_path("graphics/menu/rose-icon.png")), QtGui.QIcon.Normal,
                            QtGui.QIcon.Off)
        self.rose_button.setIcon(rose_icon)
        self.rose_button.setIconSize(QtCore.QSize(160, 160))
        self.rose_button.setCheckable(True)
        self.rose_button.setFlat(True)
        self.rose_button.setObjectName("roseButton")
        self.grid_layout_2.addWidget(self.rose_button, 0, 1, 1, 1)

        self.dave_button = QtWidgets.QPushButton(self.grid_layout_widget_2)
        self.dave_button.setStyleSheet("QPushButton {\n"
                                      "    border: none;\n"
                                      "    background-color: #efefef;\n"
                                      "}\n"
                                      "\n"
                                      "QPushButton:checked{\n"
                                      "    border-top: 2px solid #535353;\n"
                                      "    border-left: 2px solid #535353;\n"
                                      "    background-color: #c6c6c6;\n"
                                      "}")
        self.dave_button.setText("")
        dave_icon = QtGui.QIcon()
        dave_icon.addPixmap(QtGui.QPixmap(resource_path("graphics/menu/dave-icon.png")), QtGui.QIcon.Normal,
                        QtGui.QIcon.Off)
        self.dave_button.setIcon(dave_icon)
        self.dave_button.setIconSize(QtCore.QSize(160, 160))
        self.dave_button.setCheckable(True)
        self.dave_button.setFlat(True)
        self.dave_button.setObjectName("daveButton")
        self.grid_layout_2.addWidget(self.dave_button, 0, 2, 1, 1)

        self.jade_button = QtWidgets.QPushButton(self.grid_layout_widget_2)
        self.jade_button.setStyleSheet("QPushButton {\n"
                                      "    border: none;\n"
                                      "    background-color: #efefef;\n"
                                      "}\n"
                                      "\n"
                                      "QPushButton:checked{\n"
                                      "    border-top: 2px solid #535353;\n"
                                      "    border-left: 2px solid #535353;\n"
                                      "    background-color: #c6c6c6;\n"
                                      "}")
        self.jade_button.setText("")
        icon3 = QtGui.QIcon()
        icon3.addPixmap(QtGui.QPixmap(resource_path("graphics/menu/jade-icon.png")), QtGui.QIcon.Normal,
                        QtGui.QIcon.Off)
        self.jade_button.setIcon(icon3)
        self.jade_button.setIconSize(QtCore.QSize(160, 160))
        self.jade_button.setCheckable(True)
        self.jade_button.setFlat(True)
        self.jade_button.setObjectName("jadeButton")
        self.grid_layout_2.addWidget(self.jade_button, 0, 3, 1, 1)

        self.jane_button = QtWidgets.QPushButton(self.grid_layout_widget_2)
        self.jane_button.setEnabled(False)
        self.jane_button.setText("")
        self.jane_button.setIcon(icon)
        self.jane_button.setIconSize(QtCore.QSize(160, 160))
        self.jane_button.setCheckable(False)
        self.jane_button.setFlat(True)
        self.jane_button.setObjectName("janeButton")
        self.grid_layout_2.addWidget(self.jane_button, 1, 0, 1, 1)

        self.roxy_button = QtWidgets.QPushButton(self.grid_layout_widget_2)
        self.roxy_button.setEnabled(False)
        self.roxy_button.setText("")
        self.roxy_button.setIcon(icon)
        self.roxy_button.setIconSize(QtCore.QSize(160, 160))
        self.roxy_button.setCheckable(False)
        self.roxy_button.setFlat(True)
        self.roxy_button.setObjectName("roxyButton")
        self.grid_layout_2.addWidget(self.roxy_button, 1, 1, 1, 1)

        self.dirk_button = QtWidgets.QPushButton(self.grid_layout_widget_2)
        self.dirk_button.setEnabled(False)
        self.dirk_button.setText("")
        self.dirk_button.setIcon(icon)
        self.dirk_button.setIconSize(QtCore.QSize(160, 160))
        self.dirk_button.setCheckable(False)
        self.dirk_button.setFlat(True)
        self.dirk_button.setObjectName("dirkButton")
        self.grid_layout_2.addWidget(self.dirk_button, 1, 2, 1, 1)

        self.jake_button = QtWidgets.QPushButton(self.grid_layout_widget_2)
        self.jake_button.setEnabled(False)
        self.jake_button.setText("")
        self.jake_button.setIcon(icon)
        self.jake_button.setIconSize(QtCore.QSize(160, 160))
        self.jake_button.setCheckable(False)
        self.jake_button.setFlat(True)
        self.jake_button.setObjectName("jakeButton")
        self.grid_layout_2.addWidget(self.jake_button, 1, 3, 1, 1)

        self.grid_layout.addWidget(self.frame, 0, 0, 1, 1)

        # Instance the available buddies and connect their respective buttons to their spawn function
        self.john = JohnBuddy()
        self.rose = RoseBuddy()
        self.dave = DaveBuddy()
        self.jade = JadeBuddy()

        self.john_button.toggled.connect(self.spawn_john)
        self.rose_button.toggled.connect(self.spawn_rose)
        self.dave_button.toggled.connect(self.spawn_dave)
        self.jade_button.toggled.connect(self.spawn_jade)

    # Override close event for main window
    def closeEvent(self, event):
        if not self.want_to_close:  # Check if window should be minimized to tray or actually closed
            self.hide()  # Hide window instead of closing it
            # Check if window has been minimized once. If it hasn't, show a notification
            if not self.minimized_once:
                self.tray_icon.showMessage("Homestuck Buddy Selection",
                                           "Program is still running in the background. "
                                           "Exit from System Tray to close.",
                                           QtGui.QIcon(resource_path("graphics/logo.ico")))
                # Connect the message to a dummy function and then disconnect the messageClicked signal
                # This was the only way I could find to disconnect the signal in case it wasn't already connected
                # Otherwise, the program would crash
                self.tray_icon.messageClicked.connect(self.dummy)
                self.tray_icon.messageClicked.disconnect()

                # Set the minimized once variable to True so the notification is only showed once
                self.minimized_once = True

            event.ignore()  # Ignore the close event for override

    # Dummy function
    def dummy(self):
        pass

    # Actual exit function, in case the program is closed from the system tray
    def exit(self):
        self.want_to_close = True  # Set this variable to True to not override the close event
        self.worker.stop()  # Stop the thread to check for updates
        self.close()  # Actually close the window

    # Spawn the buddies
    def spawn_john(self):
        if self.john_button.isChecked():  # If the button is checked:
            self.john.init_ui()  # Initialize the buddy's UI
            self.john.show()  # Show the buddy
            self.john.end_state()  # Select a random state for the buddy
            self.active_buddies.append(self.john)  # Append the buddy to the active buddies list
        else:  # If the button is unchecked
            self.john.stop()  # Call the buddy's stop function
            self.john.close()  # Close the buddy's window
            self.active_buddies.remove(self.john)  # Remove the buddy form the active buddies list

    # Same for the other buddies
    def spawn_rose(self):
        if self.rose_button.isChecked():
            self.rose.init_ui()
            self.rose.show()
            self.rose.end_state()
            self.active_buddies.append(self.rose)
        else:
            self.rose.stop()
            self.rose.close()
            self.active_buddies.remove(self.rose)

    def spawn_dave(self):
        if self.dave_button.isChecked():
            self.dave.init_ui()
            self.dave.show()
            self.dave.end_state()
            self.active_buddies.append(self.dave)
        else:
            self.dave.stop()
            self.dave.close()
            self.active_buddies.remove(self.dave)

    def spawn_jade(self):
        if self.jade_button.isChecked():
            self.jade.init_ui()
            self.jade.show()
            self.jade.end_state()
            self.active_buddies.append(self.jade)
        else:
            self.jade.stop()
            self.jade.close()
            self.active_buddies.remove(self.jade)


class HomestuckBuddy(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set the respective graphics, default to John
        self.front_left_sprite = resource_path("graphics/john/john-front-left.png")
        self.front_right_sprite = resource_path("graphics/john/john-front-right.png")
        self.front_walk_left_sprite = resource_path("graphics/john/john-front-walk-left.gif")
        self.front_walk_right_sprite = resource_path("graphics/john/john-front-walk-right.gif")
        self.dance_sprite = resource_path("graphics/john/john-dance.gif")
        self.abscond_sprite = resource_path("graphics/john/john-abscond.gif")
        self.stupid_sprite = resource_path("graphics/john/john-stupid.gif")

        # Create variable to get the current press position when dragging
        self.__press_pos = QPoint()

    # If a new HS^2 update is detected, make the buddy perform their dance action
    def celebrate_update(self):
        # Stop the current timers
        self.timer.stop()
        if self.move_timer is not None:
            if self.move_timer.isActive():
                self.move_timer.stop()

        # Pick the dance state for the buddy
        self.pick_state("DANCE")

    def init_ui(self):
        # Make the buddy window transparent, and disable the task bar icon by setting the flag "Qt.Tool"
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.setWindowIcon(QtGui.QIcon(resource_path('graphics/logo.ico')))

        # Set the starting graphics
        self.pixmap = QPixmap(self.front_left_sprite)
        self.setPixmap(self.pixmap)

        # Create the max width and height variables
        self.max_width = 0
        self.max_height = 0

        # Loop through all current monitors to get the max width
        for m in get_monitors():
            self.max_width += m.width  # Add the current monitor width to the max width variable
            current_height = m.height  # Get the current monitor height
            self.max_height = min(current_height, m.height)  # In case monitor heights don't match, use the smallest one

        # Set the state machine
        self.state_list = ["WALK", "DANCE", "STUPID"]  # The state list
        self.state = "IDLE"  # Set the current state
        self.previous_state = self.state  # Set the previous state, variable to avoid repeating actions

        # Set the direction values for moving
        self.dir_x = -4
        self.dir_y = 4

        #Create the timers
        self.timer = QtCore.QTimer(self)
        self.move_timer = QtCore.QTimer(self)
        self.change_state_timer = QtCore.QTimer(self)
        self.moving = False
        self.setGeometry(960 - 150, 540 - 128, 300, 350)

    # Pick a state instead of randomly choosing one
    def pick_state(self, state):
        self.state = state

        self.timer.stop()
        if self.state == "WALK" and not self.moving:
            self.timer = QtCore.QTimer(self)
            self.timer.setSingleShot(True)
            self.timer.timeout.connect(self.walk)
            self.timer.start(500)

        elif self.state == "DANCE":
            self.dance()
        elif self.state == "STUPID":
            self.timer = QtCore.QTimer(self)
            self.timer.setSingleShot(True)
            self.timer.timeout.connect(self.stupid)
            self.timer.start(20)

        # Set previous state to the current state
        self.previous_state = self.state

    # Randomly choose a sate
    # I could probably use one function for randomly choosing and manually picking a state, I'll figure it out later
    def end_state(self):
        self.idle()
        self.state = random.choice(self.state_list)

        self.timer.stop()
        if self.state == "WALK" and not self.moving:
            self.timer = QtCore.QTimer(self)
            self.timer.setSingleShot(True)
            self.timer.timeout.connect(self.walk)
            self.timer.start(500)

        # If the chosen state is "Dance" or "Stupid", choose again
        elif self.state == "DANCE":
            if self.previous_state == "DANCE":
                self.end_state()
                return
            self.timer = QtCore.QTimer(self)
            self.timer.setSingleShot(True)
            self.timer.timeout.connect(self.dance)
            self.timer.start(random.randint(1, 2) * 1000)
        elif self.state == "STUPID":
            if self.previous_state == "STUPID":
                self.end_state()
                return
            self.timer = QtCore.QTimer(self)
            self.timer.setSingleShot(True)
            self.timer.timeout.connect(self.stupid)
            self.timer.start(random.randint(1, 2) * 1000)

        # Set previous state to the current state
        self.previous_state = self.state

    # Move state
    def walk(self):
        # Select a random direction
        self.dir_list = [4, -4]
        self.dir_x = random.choice(self.dir_list)
        self.dir_y = random.choice(self.dir_list)

        # Select the correct animation depending on the direction
        if self.dir_x > 0:
            self.gif = QMovie(self.front_walk_right_sprite)
        elif self.dir_x < 0:
            self.gif = QMovie(self.front_walk_left_sprite)
        self.setMovie(self.gif)
        self.gif.start()

        # Start the timers for the walk state
        self.walk_timer = QtCore.QTimer(self)
        self.walk_timer.setSingleShot(True)
        self.walk_timer.timeout.connect(self.stop_walk)
        self.walk_timer.start(2000)

        self.move_timer = QtCore.QTimer(self)
        self.move_timer.timeout.connect(self.walk_move)
        self.move_timer.start(20)

    # Move the character
    def walk_move(self):
        if self.state == "WALK":
            self.moving = True
            self.move(self.pos() + QPoint(self.dir_x, self.dir_y))

            # Bounce off the screen limits
            # Using magic numbers here, I'll fix it later
            if self.pos().x() < -75:
                self.gif = QMovie(self.front_walk_right_sprite)
                self.setMovie(self.gif)
                self.gif.start()
                self.dir_x *= -1

            if self.pos().x() > self.max_width - 225:
                self.gif = QMovie(self.front_walk_left_sprite)
                self.setMovie(self.gif)
                self.gif.start()
                self.dir_x *= -1

            if self.pos().y() < -64:
                self.dir_y *= -1

            if self.pos().y() > self.max_height - 300:
                self.dir_y *= -1

        elif self.state == "DRAG":
            self.stop_walk()

    # Stop moving
    def stop_walk(self):
        self.moving = False
        self.move_timer.stop()
        if self.state == "WALK":
            self.gif.stop()
            self.end_state()

    # THIS IS STUPID state
    def stupid(self):
        # Set the "THIS IS STUPID" animation
        self.loop_count = 0  # Initialize the animation loop count
        self.gif = QMovie(self.stupid_sprite)
        self.setMovie(self.gif)
        self.gif.start()

        self.loop_limit = random.randint(3, 5)  # Randomly choose how many times the animation should loop

        self.gif.updated.connect(self.check_for_anim_finished)  # Check every frame if the animation has finished

    # Dance state
    def dance(self):
        # Same thing for the dance animation
        self.loop_count = 0

        self.gif = QMovie(self.dance_sprite)
        self.setMovie(self.gif)
        self.gif.start()

        self.loop_limit = random.randint(2, 3)

        self.gif.updated.connect(self.check_for_anim_finished)

    def check_for_anim_finished(self):
        # Add to the loop count if the animation is finished
        if self.gif.currentFrameNumber()+1 == self.gif.frameCount():
            self.loop_count += 1

        # If the loop count is greater than or equal to the loop limit, stop the animation and randomly choose a state
        if self.loop_count >= self.loop_limit:
            self.gif.stop()
            self.end_state()

    # Idle state
    def idle(self):
        # Choose the graphics depending on the direction the character is facing
        if self.dir_x > 0:
            self.pixmap = QPixmap(self.front_right_sprite)
        elif self.dir_x < 0:
            self.pixmap = QPixmap(self.front_left_sprite)
        self.setPixmap(self.pixmap)

    # Drag state
    def drag(self):
        # Stop timers
        self.timer.stop()
        if self.move_timer is not None:
            if self.move_timer.isActive():
                self.move_timer.stop()

        self.state = "DRAG"  # Change state to Drag

        # Set the corresponding animations for the Drag state
        self.gif = QMovie(self.abscond_sprite)
        self.setMovie(self.gif)
        self.gif.start()

    def release_drag(self):
        # Stop the drag animation, and randomly choose a state
        self.gif.stop()
        self.idle()
        self.end_state()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # If the left mouse button is pressed over the character, call the drag state
            self.__press_pos = event.pos()
            self.drag()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            # If the character is released, call the releaseDrag function
            self.__press_pos = QPoint()
            self.release_drag()

    def mouseMoveEvent(self, event):
        if not self.__press_pos.isNull():
            # Check against screen limits. If it's not colliding, move the character
            # Using magic numbers here too, I'll fix it later
            if (not event.globalX() - self.__press_pos.x() < -70\
                    and not event.globalX() - self.__press_pos.x() > self.max_width - 230\
                    and not event.globalY() - self.__press_pos.y() < -60\
                    and not event.globalY() - self.__press_pos.y() > self.max_height - 310):
               self.move(self.pos() + (event.pos() - self.__press_pos))

    # Stop function called when the character is despawned
    # Instead of creating a new character object every time, it's just hidden until it's called again
    def stop(self):
        self.timer.stop()
        if self.move_timer is not None:
            if self.move_timer.isActive():
                self.move_timer.stop()
        self.state = "STOP"


class JohnBuddy(HomestuckBuddy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Assign the corresponding graphics
        self.front_left_sprite = resource_path("graphics/john/john-front-left.png")
        self.front_right_sprite = resource_path("graphics/john/john-front-right.png")
        self.front_walk_left_sprite = resource_path("graphics/john/john-front-walk-left.gif")
        self.front_walk_right_sprite = resource_path("graphics/john/john-front-walk-right.gif")
        self.dance_sprite = resource_path("graphics/john/john-dance.gif")
        self.abscond_sprite = resource_path("graphics/john/john-abscond.gif")
        self.stupid_sprite = resource_path("graphics/john/john-stupid.gif")

        self.init_ui()


class RoseBuddy(HomestuckBuddy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Assign the corresponding graphics
        self.front_left_sprite = resource_path("graphics/rose/rose-front-left.png")
        self.front_right_sprite = resource_path("graphics/rose/rose-front-right.png")
        self.front_walk_left_sprite = resource_path("graphics/rose/rose-front-walk-left.gif")
        self.front_walk_right_sprite = resource_path("graphics/rose/rose-front-walk-right.gif")
        self.dance_sprite = resource_path("graphics/rose/rose-laptop.gif")
        self.abscond_sprite = resource_path("graphics/rose/rose-abscond.gif")
        self.stupid_sprite = resource_path("graphics/rose/rose-facepalm.gif")

        self.init_ui()


class DaveBuddy(HomestuckBuddy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Assign the corresponding graphics
        self.front_left_sprite = resource_path("graphics/dave/dave-front-left.png")
        self.front_right_sprite = resource_path("graphics/dave/dave-front-right.png")
        self.front_walk_left_sprite = resource_path("graphics/dave/dave-front-walk-left.gif")
        self.front_walk_right_sprite = resource_path("graphics/dave/dave-front-walk-right.gif")
        self.dance_sprite = resource_path("graphics/dave/dave-jump.gif")
        self.abscond_sprite = resource_path("graphics/dave/dave-abscond.gif")
        self.stupid_sprite = resource_path("graphics/dave/dave-roll.gif")

        self.init_ui()


class JadeBuddy(HomestuckBuddy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Assign the corresponding graphics
        self.front_left_sprite = resource_path("graphics/jade/jade-front-left.png")
        self.front_right_sprite = resource_path("graphics/jade/jade-front-right.png")
        self.front_walk_left_sprite = resource_path("graphics/jade/jade-front-walk-left.gif")
        self.front_walk_right_sprite = resource_path("graphics/jade/jade-front-walk-right.gif")
        self.dance_sprite = resource_path("graphics/jade/jade-bass.gif")
        self.abscond_sprite = resource_path("graphics/jade/jade-abscond.gif")
        self.stupid_sprite = resource_path("graphics/jade/jade-sleep.gif")

        self.init_ui()


def main():
    random.seed(None)  # Randomize the seed

    # Create the application
    app = QApplication(sys.argv)
    w = BuddySelection()
    w.show()

    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())
