import sys
import os
import configparser
import html

import requests

from PySide.QtCore import (
    Qt,
    QSize
)

from PySide.QtGui import (
    QApplication,
    QMainWindow,
    QWidget,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QLineEdit,
    QPushButton,
    QLabel,
    QMessageBox,
    QSplitter,
    QFrame,
    QGroupBox,
    QAction,
    QToolBar,
    QStatusBar,
    QFont,
    QIcon
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


def resource_path(name):

    if hasattr(sys, "_MEIPASS"):

        return os.path.join(
            sys._MEIPASS,
            name
        )

    return os.path.join(
        BASE_DIR,
        name
    )


# ============================================================
# CONFIG
# ============================================================

config = configparser.ConfigParser()

config_file = resource_path(
    "config.ini"
)

config.read(
    config_file
)


if not config.has_section(
    "discord"
):

    raise RuntimeError(
        "config.ini was not found or does not contain "
        "a [discord] section.\n\n"
        "Expected:\n"
        "[discord]\n"
        "bot_token=YOUR_BOT_TOKEN"
    )


if not config.has_option(
    "discord",
    "bot_token"
):

    raise RuntimeError(
        "config.ini does not contain a bot_token "
        "under the [discord] section."
    )


BOT_TOKEN = config.get(
    "discord",
    "bot_token"
).strip()


DISCORD_API = (
    "https://discord.com/api/v10"
)


# ============================================================
# DISCORD BOT CLIENT
# ============================================================

class DiscordClient(object):

    def __init__(self):

        self.bot_token = BOT_TOKEN
        self.user = None


    def headers(self):

        return {
            "Authorization": (
                "Bot " + self.bot_token
            ),
            "User-Agent": (
                "AeroCord/0.6.1.1"
            ),
            "Accept": (
                "application/json"
            )
        }


    def request(
        self,
        method,
        endpoint,
        **kwargs
    ):

        url = (
            DISCORD_API
            + endpoint
        )

        headers = self.headers()

        extra_headers = kwargs.pop(
            "headers",
            {}
        )

        headers.update(
            extra_headers
        )

        if "json" in kwargs:

            headers["Content-Type"] = (
                "application/json"
            )

        response = requests.request(
            method,
            url,
            headers=headers,
            timeout=15,
            **kwargs
        )

        if not response.ok:

            try:

                data = response.json()

                message = data.get(
                    "message",
                    response.text
                )

            except Exception:

                message = response.text

            raise RuntimeError(
                "Discord API error {}: {}".format(
                    response.status_code,
                    message
                )
            )

        if not response.content:

            return None

        try:

            return response.json()

        except Exception:

            return response.text


    # --------------------------------------------------------
    # Bot account
    # --------------------------------------------------------

    def get_current_user(self):

        data = self.request(
            "GET",
            "/users/@me"
        )

        self.user = data

        return data


    # --------------------------------------------------------
    # Servers
    # --------------------------------------------------------

    def get_guilds(self):

        return self.request(
            "GET",
            "/users/@me/guilds"
        )


    # --------------------------------------------------------
    # Channels
    # --------------------------------------------------------

    def get_channels(
        self,
        guild_id
    ):

        return self.request(
            "GET",
            "/guilds/{}/channels".format(
                guild_id
            )
        )


    # --------------------------------------------------------
    # Messages
    # --------------------------------------------------------

    def get_messages(
        self,
        channel_id
    ):

        return self.request(
            "GET",
            "/channels/{}/messages?limit=50".format(
                channel_id
            )
        )


    # --------------------------------------------------------
    # Send message
    # --------------------------------------------------------

    def send_message(
        self,
        channel_id,
        content
    ):

        return self.request(
            "POST",
            "/channels/{}/messages".format(
                channel_id
            ),
            json={
                "content": content
            }
        )


# ============================================================
# MAIN WINDOW
# ============================================================

class MainWindow(QMainWindow):

    def __init__(self):

        QMainWindow.__init__(
            self
        )

        self.discord = DiscordClient()

        self.guilds = []
        self.channels = []

        self.current_guild = None
        self.current_channel = None

        self.setWindowTitle(
            "AeroCord"
        )

        self.resize(
            1200,
            760
        )

        self.setMinimumSize(
            900,
            600
        )

        self.build_menus()
        self.build_toolbar()
        self.build_ui()
        self.build_statusbar()

        self.set_ui_connected(
            False
        )

        self.connect_bot()


    # ========================================================
    # MENUS
    # ========================================================

    def build_menus(self):

        file_menu = self.menuBar().addMenu(
            "File"
        )


        refresh_action = QAction(
            "Refresh",
            self
        )

        refresh_action.setShortcut(
            "F5"
        )

        refresh_action.triggered.connect(
            self.refresh
        )

        self.refresh_action = (
            refresh_action
        )

        file_menu.addAction(
            refresh_action
        )

        file_menu.addSeparator()


        exit_action = QAction(
            "Exit",
            self
        )

        exit_action.triggered.connect(
            self.close
        )

        file_menu.addAction(
            exit_action
        )


        view_menu = self.menuBar().addMenu(
            "View"
        )

        view_menu.addAction(
            refresh_action
        )


        tools_menu = self.menuBar().addMenu(
            "Tools"
        )

        reconnect_action = QAction(
            "Reconnect",
            self
        )

        reconnect_action.triggered.connect(
            self.connect_bot
        )

        tools_menu.addAction(
            reconnect_action
        )


        help_menu = self.menuBar().addMenu(
            "Help"
        )

        about_action = QAction(
            "About AeroCord",
            self
        )

        about_action.triggered.connect(
            self.show_about
        )

        help_menu.addAction(
            about_action
        )


    # ========================================================
    # TOOLBAR
    # ========================================================

    def build_toolbar(self):

        toolbar = QToolBar(
            "Main Toolbar",
            self
        )

        toolbar.setIconSize(
            QSize(16, 16)
        )

        self.addToolBar(
            toolbar
        )


        refresh_button = QAction(
            "Refresh",
            self
        )

        refresh_button.triggered.connect(
            self.refresh
        )

        toolbar.addAction(
            refresh_button
        )

        toolbar.addSeparator()


        self.toolbar_status = QLabel(
            "Connecting..."
        )

        toolbar.addWidget(
            self.toolbar_status
        )


    # ========================================================
    # UI
    # ========================================================

    def build_ui(self):

        central = QWidget()

        self.setCentralWidget(
            central
        )

        main_layout = QHBoxLayout(
            central
        )

        main_layout.setContentsMargins(
            6,
            6,
            6,
            6
        )

        main_layout.setSpacing(
            6
        )


        # ----------------------------------------------------
        # SERVERS
        # ----------------------------------------------------

        server_box = QGroupBox(
            "Servers"
        )

        server_layout = QVBoxLayout(
            server_box
        )

        self.server_list = QListWidget()

        self.server_list.itemClicked.connect(
            self.server_clicked
        )

        server_layout.addWidget(
            self.server_list
        )


        # ----------------------------------------------------
        # CHANNELS
        # ----------------------------------------------------

        channel_box = QGroupBox(
            "Channels"
        )

        channel_layout = QVBoxLayout(
            channel_box
        )


        self.server_name = QLabel(
            "No server selected"
        )

        self.server_name.setFrameStyle(
            QFrame.Panel |
            QFrame.Sunken
        )

        channel_layout.addWidget(
            self.server_name
        )


        self.channel_list = QListWidget()

        self.channel_list.itemClicked.connect(
            self.channel_clicked
        )

        channel_layout.addWidget(
            self.channel_list
        )


        # ----------------------------------------------------
        # CONVERSATION
        # ----------------------------------------------------

        conversation_box = QGroupBox(
            "Conversation"
        )

        conversation_layout = QVBoxLayout(
            conversation_box
        )


        self.chat_title = QLabel(
            "No channel selected"
        )

        title_font = self.chat_title.font()

        title_font.setBold(
            True
        )

        self.chat_title.setFont(
            title_font
        )

        conversation_layout.addWidget(
            self.chat_title
        )


        self.channel_type = QLabel(
            ""
        )

        conversation_layout.addWidget(
            self.channel_type
        )


        line = QFrame()

        line.setFrameShape(
            QFrame.HLine
        )

        line.setFrameShadow(
            QFrame.Sunken
        )

        conversation_layout.addWidget(
            line
        )


        self.message_view = QTextEdit()

        self.message_view.setReadOnly(
            True
        )

        conversation_layout.addWidget(
            self.message_view
        )


        input_layout = QHBoxLayout()


        self.message_input = QLineEdit()

        self.message_input.setPlaceholderText(
            "Type a message..."
        )

        self.message_input.returnPressed.connect(
            self.send_message
        )

        input_layout.addWidget(
            self.message_input
        )


        self.send_button = QPushButton(
            "Send"
        )

        self.send_button.clicked.connect(
            self.send_message
        )

        input_layout.addWidget(
            self.send_button
        )


        conversation_layout.addLayout(
            input_layout
        )


        # ----------------------------------------------------
        # SPLITTERS
        # ----------------------------------------------------

        left_splitter = QSplitter(
            Qt.Horizontal
        )

        left_splitter.addWidget(
            server_box
        )

        left_splitter.addWidget(
            channel_box
        )

        left_splitter.setSizes(
            [
                180,
                300
            ]
        )


        main_splitter = QSplitter(
            Qt.Horizontal
        )

        main_splitter.addWidget(
            left_splitter
        )

        main_splitter.addWidget(
            conversation_box
        )

        main_splitter.setSizes(
            [
                500,
                700
            ]
        )


        main_layout.addWidget(
            main_splitter
        )


    # ========================================================
    # STATUS BAR
    # ========================================================

    def build_statusbar(self):

        status = QStatusBar()

        self.setStatusBar(
            status
        )

        status.showMessage(
            "Ready"
        )


        self.connection_label = QLabel(
            "Not connected"
        )

        status.addPermanentWidget(
            self.connection_label
        )


    # ========================================================
    # USERNAME COLORS
    # ========================================================

    def get_username_color(
        self,
        user_id
    ):

        colors = [
            "#E85D04",
            "#1976D2",
            "#B8860B",
            "#43A047"
        ]

        try:

            return colors[
                int(user_id) % len(colors)
            ]

        except Exception:

            return "#1976D2"


    # ========================================================
    # CONNECTION STATE
    # ========================================================

    def set_ui_connected(
        self,
        connected
    ):

        self.server_list.setEnabled(
            connected
        )

        self.channel_list.setEnabled(
            connected
        )

        self.message_input.setEnabled(
            connected
        )

        self.send_button.setEnabled(
            connected
        )


        if connected:

            username = self.discord.user.get(
                "username",
                "AeroCord Bot"
            )

            self.connection_label.setText(
                "Connected: {}".format(
                    username
                )
            )

            self.toolbar_status.setText(
                "Connected to Discord"
            )

        else:

            self.connection_label.setText(
                "Not connected"
            )

            self.toolbar_status.setText(
                "Disconnected"
            )


    # ========================================================
    # CONNECT BOT
    # ========================================================

    def connect_bot(self):

        if not BOT_TOKEN:

            QMessageBox.critical(
                self,
                "AeroCord",
                "No bot token was found in config.ini."
            )

            return


        self.toolbar_status.setText(
            "Connecting bot..."
        )

        self.statusBar().showMessage(
            "Connecting to Discord..."
        )

        self.refresh_action.setEnabled(
            False
        )


        try:

            user = (
                self.discord.get_current_user()
            )

            self.bot_connected(
                user,
                None
            )

        except Exception as error:

            self.set_ui_connected(
                False
            )

            self.refresh_action.setEnabled(
                True
            )

            self.statusBar().showMessage(
                "Connection failed"
            )

            QMessageBox.critical(
                self,
                "Discord Bot Error",
                "{}: {}".format(
                    type(error).__name__,
                    str(error)
                )
            )


    # ========================================================
    # BOT CONNECTED
    # ========================================================

    def bot_connected(
        self,
        user,
        error
    ):

        self.refresh_action.setEnabled(
            True
        )


        if error:

            self.set_ui_connected(
                False
            )

            QMessageBox.critical(
                self,
                "Discord Bot Error",
                str(error)
            )

            return


        self.discord.user = user

        self.set_ui_connected(
            True
        )


        username = user.get(
            "username",
            "AeroCord Bot"
        )


        self.statusBar().showMessage(
            "Connected to Discord as {}".format(
                username
            )
        )


        self.load_guilds()


    # ========================================================
    # SERVERS
    # ========================================================

    def load_guilds(self):

        self.server_list.clear()

        self.channel_list.clear()

        self.message_view.clear()

        self.server_name.setText(
            "Loading servers..."
        )


        try:

            guilds = (
                self.discord.get_guilds()
            )

            self.guilds_loaded(
                guilds,
                None
            )

        except Exception as error:

            self.guilds_loaded(
                None,
                error
            )


    def guilds_loaded(
        self,
        guilds,
        error
    ):

        if error:

            self.server_name.setText(
                "Unable to load servers"
            )

            QMessageBox.critical(
                self,
                "Server Error",
                str(error)
            )

            return


        self.guilds = guilds or []

        self.server_list.clear()


        for guild in self.guilds:

            name = guild.get(
                "name",
                "Unknown Server"
            )

            item = QListWidgetItem(
                name
            )

            item.setData(
                Qt.UserRole,
                guild.get("id")
            )

            self.server_list.addItem(
                item
            )


        self.server_name.setText(
            "{} server(s)".format(
                len(self.guilds)
            )
        )

        self.statusBar().showMessage(
            "{} server(s) loaded".format(
                len(self.guilds)
            )
        )


    # ========================================================
    # SERVER CLICKED
    # ========================================================

    def server_clicked(
        self,
        item
    ):

        guild_id = item.data(
            Qt.UserRole
        )

        if not guild_id:

            return


        self.current_guild = guild_id

        self.current_channel = None

        self.message_view.clear()

        self.chat_title.setText(
            "No channel selected"
        )

        self.channel_type.setText(
            ""
        )

        self.server_name.setText(
            item.text()
        )

        self.channel_list.clear()


        loading_item = QListWidgetItem(
            "Loading channels..."
        )

        loading_item.setFlags(
            Qt.NoItemFlags
        )

        self.channel_list.addItem(
            loading_item
        )


        try:

            channels = (
                self.discord.get_channels(
                    guild_id
                )
            )

            self.channels_loaded(
                channels,
                None
            )

        except Exception as error:

            self.channels_loaded(
                None,
                error
            )


    # ========================================================
    # ADD CHANNEL ITEM
    # ========================================================

    def add_channel_item(
        self,
        channel,
        indent=False
    ):

        name = channel.get(
            "name",
            "Unnamed"
        )

        channel_type = channel.get(
            "type"
        )


        prefix = "# "


        if indent:

            text = (
                "    "
                + prefix
                + name
            )

        else:

            text = (
                prefix
                + name
            )


        item = QListWidgetItem(
            text
        )

        item.setData(
            Qt.UserRole,
            channel.get("id")
        )

        item.setData(
            Qt.UserRole + 1,
            channel_type
        )

        self.channel_list.addItem(
            item
        )


    # ========================================================
    # CHANNELS LOADED
    # ========================================================

    def channels_loaded(
        self,
        channels,
        error
    ):

        if error:

            self.channel_list.clear()

            error_item = QListWidgetItem(
                "Unable to load channels"
            )

            error_item.setFlags(
                Qt.NoItemFlags
            )

            self.channel_list.addItem(
                error_item
            )

            QMessageBox.critical(
                self,
                "Channel Error",
                str(error)
            )

            return


        self.channels = channels or []

        self.channel_list.clear()

        categories = {}

        uncategorized = []


        for channel in self.channels:

            channel_type = channel.get(
                "type"
            )


            if channel_type == 4:

                categories[
                    channel.get("id")
                ] = channel


            elif channel_type in (
                0,
                5,
                15
            ):

                parent_id = channel.get(
                    "parent_id"
                )

                if parent_id:

                    continue

                uncategorized.append(
                    channel
                )


        uncategorized.sort(
            key=lambda channel: (
                channel.get(
                    "position",
                    0
                ),
                channel.get(
                    "id",
                    ""
                )
            )
        )


        for channel in uncategorized:

            self.add_channel_item(
                channel
            )


        category_list = list(
            categories.values()
        )

        category_list.sort(
            key=lambda category: (
                category.get(
                    "position",
                    0
                ),
                category.get(
                    "id",
                    ""
                )
            )
        )


        for category in category_list:

            category_name = category.get(
                "name",
                "CATEGORY"
            )


            category_item = QListWidgetItem(
                category_name.upper()
            )

            category_item.setFlags(
                Qt.NoItemFlags
            )

            self.channel_list.addItem(
                category_item
            )


            children = []

            category_id = category.get(
                "id"
            )


            for channel in self.channels:

                if channel.get(
                    "parent_id"
                ) != category_id:

                    continue


                if channel.get(
                    "type"
                ) not in (
                    0,
                    5,
                    15
                ):

                    continue


                children.append(
                    channel
                )


            children.sort(
                key=lambda channel: (
                    channel.get(
                        "position",
                        0
                    ),
                    channel.get(
                        "id",
                        ""
                    )
                )
            )


            for channel in children:

                self.add_channel_item(
                    channel,
                    True
                )


        self.statusBar().showMessage(
            "{} channel(s) loaded".format(
                len(self.channels)
            )
        )


    # ========================================================
    # CHANNEL CLICKED
    # ========================================================

    def channel_clicked(
        self,
        item
    ):

        channel_id = item.data(
            Qt.UserRole
        )

        if not channel_id:

            return


        channel_type = item.data(
            Qt.UserRole + 1
        )

        self.current_channel = (
            channel_id
        )


        title = item.text().strip()


        if title.startswith(
            "# "
        ):

            title = title[2:]


        self.chat_title.setText(
            title
        )


        if channel_type == 5:

            self.channel_type.setText(
                "Announcement channel"
            )

        elif channel_type == 15:

            self.channel_type.setText(
                "Forum channel"
            )

        else:

            self.channel_type.setText(
                "Text channel"
            )


        self.message_view.clear()

        self.message_view.setPlainText(
            "Loading messages..."
        )


        try:

            messages = (
                self.discord.get_messages(
                    channel_id
                )
            )

            self.messages_loaded(
                messages,
                None
            )

        except Exception as error:

            self.messages_loaded(
                None,
                error
            )


    # ========================================================
    # MESSAGES LOADED
    # ========================================================

    def messages_loaded(
        self,
        messages,
        error
    ):

        if error:

            self.message_view.setPlainText(
                "Unable to load messages.\n\n{}".format(
                    error
                )
            )

            return


        self.message_view.clear()

        messages = messages or []


        try:

            messages.reverse()

        except Exception:

            pass


        current_guild = None


        for guild in self.guilds:

            if guild.get(
                "id"
            ) == self.current_guild:

                current_guild = guild

                break


        for message in messages:

            author = message.get(
                "author",
                {}
            )


            user_id = author.get(
                "id",
                "0"
            )


            username = author.get(
                "global_name"
            )


            if not username:

                username = author.get(
                    "username",
                    "Unknown User"
                )


            content = message.get(
                "content",
                ""
            )


            content = html.escape(
                str(content)
            )

            username = html.escape(
                str(username)
            )


            username_color = (
                self.get_username_color(
                    user_id
                )
            )


            owner_badge = ""

            if (
                current_guild
                and user_id == current_guild.get(
                    "owner_id"
                )
            ):

                owner_badge = (
                    " <b style='color: #D4A017;'>"
                    "👑 Owner"
                    "</b>"
                )


            self.message_view.append(
                "<span style='color: {}; "
                "font-weight: bold;'>"
                "{}</span>{}: {}".format(
                    username_color,
                    username,
                    owner_badge,
                    content
                )
            )

            self.message_view.append(
                ""
            )


        self.statusBar().showMessage(
            "{} message(s) loaded".format(
                len(messages)
            )
        )


    # ========================================================
    # SEND MESSAGE
    # ========================================================

    def send_message(self):

        if not self.current_channel:

            return


        content = (
            self.message_input.text().strip()
        )


        if not content:

            return


        self.message_input.clear()

        self.send_button.setEnabled(
            False
        )

        self.statusBar().showMessage(
            "Sending..."
        )


        try:

            message = (
                self.discord.send_message(
                    self.current_channel,
                    content
                )
            )

            self.message_sent(
                message,
                None
            )

        except Exception as error:

            self.message_sent(
                None,
                error
            )


    # ========================================================
    # MESSAGE SENT
    # ========================================================

    def message_sent(
        self,
        message,
        error
    ):

        self.send_button.setEnabled(
            True
        )


        if error:

            self.statusBar().showMessage(
                "Failed to send message"
            )

            QMessageBox.critical(
                self,
                "Message Error",
                str(error)
            )

            return


        self.statusBar().showMessage(
            "Message sent"
        )


        if message:

            author = message.get(
                "author",
                {}
            )


            user_id = author.get(
                "id",
                "0"
            )


            username = author.get(
                "global_name"
            )


            if not username:

                username = author.get(
                    "username",
                    "AeroCord Bot"
                )


            content = message.get(
                "content",
                ""
            )


            username_color = (
                self.get_username_color(
                    user_id
                )
            )


            username = html.escape(
                str(username)
            )

            content = html.escape(
                str(content)
            )


            self.message_view.append(
                "<span style='color: {}; "
                "font-weight: bold;'>"
                "{}</span>: {}".format(
                    username_color,
                    username,
                    content
                )
            )

            self.message_view.append(
                ""
            )


    # ========================================================
    # REFRESH
    # ========================================================

    def refresh(self):

        if not self.discord.user:

            self.connect_bot()

            return


        self.load_guilds()


    # ========================================================
    # ABOUT
    # ========================================================

    def show_about(self):

        QMessageBox.about(
            self,
            "About AeroCord",
            "<div style='font-family: Segoe UI;'>"
            "<div style='font-size: 20px; "
            "font-weight: bold;'>"
            "AeroCord"
            "</div>"
            "<div style='font-size: 11px; "
            "color: #555555;'>"
            "Version 0.6.1"
            "</div>"
            "<br>"
            "<div style='font-size: 10px;'>"
            "A revolutionary Discord client for Windows XP."
            "</div>"
            "<br>"
            "<div style='font-size: 10px;'>"
            "Created with Python and PySide."
            "</div>"
            "</div>"
        )


# ============================================================
# APPLICATION
# ============================================================

def main():

    app = QApplication(
        sys.argv
    )


    app.setApplicationName(
        "AeroCord"
    )


    icon_path = resource_path(
        "AeroCord.ico"
    )


    if os.path.exists(
        icon_path
    ):

        app.setWindowIcon(
            QIcon(
                icon_path
            )
        )


    app.setStyle(
        "Fusion"
    )


    app.setFont(
        QFont(
            "Segoe UI",
            9
        )
    )


    window = MainWindow()

    window.show()


    return app.exec_()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    sys.exit(
        main()
    )