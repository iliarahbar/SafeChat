from session import *
from ui import *
from dialog_ui import Ui_Dialog
import sys

class SecondDialog(QtWidgets.QDialog, Ui_Dialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

class Bridge(QtCore.QObject):
    call_in_main = QtCore.pyqtSignal(object, tuple, dict)

class Client(QtWidgets.QMainWindow, SSession):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        SSession.__init__(self)
        
        self.s = self.connect(SERVERIP, SERVERPORT)

        self.ui = Ui_SafeChat()
        self.ui.setupUi(self)

        self.di = SecondDialog()

        self.setCentralWidget(self.ui.stackedWidget)
        self.ui.stackedWidget.setCurrentIndex(0)

        self.setupSignals()

        self.deficon = QtGui.QIcon()
        self.deficon.addPixmap(QtGui.QPixmap("misc/profile.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.On)

        self.ul = {}
        self.cur = None
        self.msg = {}
        self.name = {}
        self.bio = {}

    def setupSignals(self):
        self.ui.pushButton.clicked.connect(self.signin)
        self.ui.pushButton_2.clicked.connect(lambda :self.ui.stackedWidget.setCurrentIndex(1))
        self.ui.pushButton_3.clicked.connect(lambda :self.ui.stackedWidget.setCurrentIndex(0))
        self.ui.pushButton_4.clicked.connect(self.signup)
        self.ui.pushButton_8.clicked.connect(self.sendMsg)
        self.ui.pushButton_6.clicked.connect(lambda :self.profile(self.user))
        self.ui.pushButton_9.clicked.connect(lambda :self.profile(self.cur))
        self.ui.pushButton_7.clicked.connect(self.newc)
        self.di.pushButton_4.clicked.connect(self.addc)
        self.di.pushButton.clicked.connect(self.sendSet)
        self.ui.pushButton_5.clicked.connect(self.sett)

    def sett(self):
        self.di.stackedWidget.setCurrentIndex(0)

        self.send(self.s, b'\x05' + self.user.encode())

        data = self.recv(self.s)

        name, bio = data[1:].decode().split('\x07')[:2]
        
        self.di.lineEdit.setText(self.user)
        self.di.lineEdit_2.setText(name)
        self.di.plainTextEdit.setPlainText(bio)

        return self.di.exec()

    def sendSet(self):

        nuser = self.di.lineEdit.text()
        nname = self.di.lineEdit_2.text()
        nbio = self.di.plainTextEdit.toPlainText()
        
        self.send(self.s, b'\x04' + '\x07'.join([self.user, nuser, nname, nbio]).encode())

        data = self.recv(self.s)

        if (data[0] == 3):
            self.di.label_5.setText("Username is Taken.")
            return 0

        self.di.close()

        self.user = nuser

        self.ui.pushButton_6.setText("@"+self.user)

    def signin(self):
        user = self.ui.lineEdit.text()
        pw = self.ui.lineEdit_2.text()
        
        if (len(user) == 0 or len(pw) == 0):
            self.ui.label_2.setText("Please enter username and password.")
            return 0

        self.send(self.s, b'\x02' + self.md5(pw) + user.encode())

        resp = self.recv(self.s)

        if (resp[0] == 1):
            self.ui.label_2.setText("Username or password is incorrect.")
            return 0

        if (resp[0] == 2):
            self.user = user
            
            self.loadMain()

            return 1

        print("SIGN IN BAD CASE")

        return 0

    def newc(self):
        self.di.stackedWidget.setCurrentIndex(2)

        self.di.lineEdit_4.setText('')

        return self.di.exec()

    def addc(self):
        user = self.di.lineEdit_4.text()
        
        self.send(self.s, b'\x05' + user.encode())

        data = self.recv(self.s)

        if (data[0] == 3):
            self.di.label_4.setText("Username not found.")
            return 0;

        self.di.close()
        
        self.ul[user] = None
        self.msg[user] = []
        self.newContact(user)

    def signup(self):
        user = self.ui.lineEdit_3.text()
        pw = self.ui.lineEdit_4.text()
        pwc = self.ui.lineEdit_5.text()

        if (len(user) == 0 or len(pw) == 0 or len(pwc) == 0):
            self.ui.label_3.setText("Please enter username and password.")
            return 0

        if (pw != pwc):
            self.ui.label_3.setText("Password did not match.")
            return 0

        self.send(self.s, b'\x01' + user.encode() + b'\x07' + pw.encode())

        resp = self.recv(self.s)
        
        if (resp[0] == 1):
            self.ui.label_3.setText("Username is taken.")
            return 0
        
        if (resp[0] == 2):
            self.ui.label_3.setText("Account created. You can sign in now.")
            return 1

        print("SIGN UP BAD CASE")

        return 0

    def loadMain(self):
        self.ui.stackedWidget.setCurrentIndex(2)

        self.ui.pushButton_9.setText("")
        self.ui.pushButton_9.setIcon(QtGui.QIcon())

        self.ui.pushButton_6.setText("@"+self.user)
        self.ui.pushButton_6.setIcon(self.geticon(self.user))
        
        t = Thread(target=self.listen, daemon=1)
            
        t.start()

    def geticon(self, user):
        icon = QtGui.QIcon()
    
        try:
            open(f"misc/{user}.jpg")

            icon.addPixmap(QtGui.QPixmap(f"misc/{user}.jpg"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.On)
        except:
            icon.addPixmap(QtGui.QPixmap(f"misc/profile.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.On)
        
        return icon

    def listen(self):

        while 1:
            data = self.recv(self.s)
            
            if len(data) == 0:
                break

            if data[0] == 0:
                return socket.close()
        
            if data[0] == 1:
                for d in data[1:].split(b'\x01'):
                    self.newMsg(d)

        self.s.close()

    def newMsg(self, data):
        sender, recver, msg = data.decode().split('\x07')
        
        ou = (recver if sender == self.user else sender)

        if (not ou in self.ul):
            self.ul[ou] = None
            self.msg[ou] = []
            bridge.call_in_main.emit(self.newContact, (ou,), {})

        self.msg[ou].append(data)

        if (self.cur == ou):
            bridge.call_in_main.emit(self.showMsg, (data,), {})

    def profile(self, user):
        if (not user):
            return 0

        self.send(self.s, b'\x05' + user.encode())

        data = self.recv(self.s)

        name, bio = data[1:].decode().split('\x07')[:2]
        
        self.di.stackedWidget.setCurrentIndex(1)

        self.di.label.setText('@' + user)
        self.di.label_2.setText(name)
        self.di.textBrowser.setText(bio)
        self.di.label_3.setPixmap(self.geticon(user).pixmap(256, 256))

        return self.di.exec()

    def newContact(self, username):
        item = QtWidgets.QListWidgetItem()
        item.setSizeHint(QtCore.QSize(0, 50))
        
        self.ui.listWidget_3.addItem(item)

        btn = QtWidgets.QPushButton('@' + username)
        btn.setMinimumSize(QtCore.QSize(0, 50))
        btn.setCheckable(1)
        btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        btn.setStyleSheet("QPushButton {\n"
"    background-color: #222222;\n"
"    border-radius: 0px;\n"
    "border-top: 1px solid #111111;\n"
    "border-bottom: 1px solid #111111;\n"
"    text-align:left;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: #333333;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: #111111;\n"
"    outline: none;\n"
"}\n"
"\n"
"QPushButton:checked {\n"
"    background-color: #111111;\n"
"    outline: none;\n"
"}\n"
"")
        btn.setIcon(self.geticon(username))
        btn.setIconSize(QtCore.QSize(45, 45))

        btn.clicked.connect(lambda :self.switch(username))

        self.ui.listWidget_3.setItemWidget(item, btn)
    
        self.ul[username] = btn

    def switch(self, username):
        if (self.cur):
            self.ul[self.cur].setChecked(0)
        
        self.cur = username
        self.ul[username].setChecked(1)

        self.ui.pushButton_9.setText('@' + self.cur)
        self.ui.pushButton_9.setIcon(self.geticon(self.cur))

        bridge.call_in_main.emit(self.loadMsg, (), {})

    def loadMsg(self):
        self.ui.listWidget.clear()

        for msg in self.msg[self.cur]:
            self.showMsg(msg)

    def showMsg(self, data):
        sender, recver, msg = data.decode().split('\x07')
        
        cont = ""

        for i in range(0, len(msg), 30):
            cont += msg[i : min(i + 30, len(msg))] + '\n'

        cont = cont[:-1]

        item = QtWidgets.QListWidgetItem()
        item.setSizeHint(QtCore.QSize(0, (cont.count('\n') + 4) * 17))
        
        self.ui.listWidget.addItem(item)

        lbl = QtWidgets.QLabel(cont)
        lbl.setSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Preferred)

        sp = QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)

        if (self.user == sender):
            lbl.setStyleSheet("background-color: #333333;\n"
"border-radius: 10px;\n"
"padding: 5px;")

            layout.addItem(sp)
            layout.addWidget(lbl)

        else:
            lbl.setStyleSheet("background-color: #222222;\n"
"border-radius: 10px;\n"
"padding: 5px;")
            
            layout.addWidget(lbl)
            layout.addItem(sp)
        
        container = QtWidgets.QWidget()
        container.setLayout(layout)

        self.ui.listWidget.setItemWidget(item, container)
        self.ui.listWidget.scrollToBottom()

    def sendMsg(self):
        msg = self.ui.lineEdit_6.text()

        if (len(msg) == 0):
            return 0

        self.ui.lineEdit_6.setText("")

        self.send(self.s, b'\x03' + '\x07'.join([self.user, self.cur, msg]).encode())

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    bridge = Bridge()
    bridge.call_in_main.connect(lambda fn, args, kwargs: fn(*args, **kwargs))

    win = Client()
    win.show()

    sys.exit(app.exec())
