from session import *
from sqlalchemy.orm import *
from sqlalchemy import *

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'Users'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str]
    pw: Mapped[str]
    name: Mapped[str]
    bio: Mapped[str]

class Msg(Base):
    __tablename__ = 'messages'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sender: Mapped[str]
    recver: Mapped[str]
    data: Mapped[str]

class MsgDB:
    def __init__(self):
        self.engine = create_engine("sqlite:///server.db")
        
        Base.metadata.create_all(self.engine)

        self.ses = Session(self.engine)

    def addUser(self, username, pw, name="", bio=""):
        if len(self.getUser(username)) > 0:
            return 0

        self.ses.add(User(username=username, pw=pw, name=name, bio=bio))
        self.ses.commit()

        return 1

    def getUser(self, username):
        return self.ses.execute(select(User).where(User.username == username)).scalars().all()

    def addMsg(self, sender, recver, data):
        self.ses.add(Msg(sender=sender, recver=recver, data=data))
        self.ses.commit()

        return self.getMsg(sender)[-1]

    def getMsg(self, user):
        return self.ses.execute(select(Msg).where(or_(Msg.sender==user, Msg.recver==user))).scalars().all()

class Server(SSession):
    def __init__(self):
        SSession.__init__(self)
        
        self.s = socket.socket()
        self.s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.s.bind((SERVERIP, SERVERPORT))
        self.s.listen()

        self.db = MsgDB()

        self.sl = {}

    def listen(self):
        print("Waiting for clients...")

        while 1:
            csocket, caddr = self.s.accept()
            
            print(f"Client {caddr} connected.")

            t = Thread(target=self.handleClient, args=[csocket], daemon=1)
            
            t.start()

    def handleClient(self, socket):
        user = None

        while 1:
            data = self.recv(socket)
            
            if len(data) == 0:
                break

            if data == 0:
                return socket.close()
        
            if data[0] == 1:
                self.signup(socket, data)
            
            if data[0] == 2:
                user = self.signin(socket, data)

            if data[0] == 3 and user:
                self.newMsg(data)

            if data[0] == 4 and user:
                self.updUser(socket, data)

            if data[0] == 5:
                self.sendUser(socket, data[1:].decode())

        self.logout(socket, user)

    def updUser(self, socket, data):
        user, nuser, nname, nbio = data[1:].decode().split('\x07')
        if (user != nuser and len(self.db.getUser(nuser)) > 0):
            for i in range(5):
                self.send(socket, b'\x03')

            return 0
    
        ul = self.db.getUser(user)[0]
    
        ul.username = nuser
        ul.name = nname
        ul.bio = nbio

        self.db.ses.commit()
        
        for i in range(5):
            self.send(socket, b'\x04')

    def sendUser(self, socket, user):
        ul = self.db.getUser(user)

        print(ul)

        if (len(ul) == 0):
            for i in range(5):
                self.send(socket, b'\x03')
            
            return 0

        for i in range(5):
            self.send(socket, b'\x02' + ul[0].name.encode() + b'\x07' + ul[0].bio.encode())

    def newMsg(self, data):
        sender, recver, msg = data[1:].decode().split('\x07')

        ref = self.db.addMsg(sender, recver, msg)
        
        for soc in self.sl[sender]:
            self.sendMsg(soc, ref)

        if (recver in self.sl):
            for soc in self.sl[recver]:
                self.sendMsg(soc, ref)

    def signup(self, socket, data):
        user, pw = data[1:].decode().split('\x07')
        
        if self.db.addUser(user, pw) == 0:
            self.send(socket, b'\x01')
            return 0;

        self.send(socket, b'\x02')
        return 1

    def signin(self, socket, data):
        hp = data[1:17]
        user = data[17:].decode()

        ul = self.db.getUser(user)

        if len(ul) == 0 or hp != self.md5(ul[0].pw):
            self.send(socket, b'\x01')
            return None;

        self.send(socket, b'\x02')
    
        if (user not in self.sl):
            self.sl[user] = []
        
        self.sl[user].append(socket)
        
        self.sendDB(socket, user)
    
        return user

    def sendDB(self, socket, user):

        ml = self.db.getMsg(user)

        for msg in ml:
            self.sendMsg(socket, msg)

    def sendMsg(self, socket, msg):
        self.send(socket, b'\x01' + msg.sender.encode() + b'\x07' + msg.recver.encode() + b'\x07' + msg.data.encode())
            
    def logout(self, socket, user):

        self.sl[user].remove(socket)

        socket.close()

        print(f"Client {user} exited.")
        
if __name__ == "__main__":
    ser = Server()

    ser.db.addMsg("mtmt", "ilia", "few")
    ser.db.addMsg("noli", "ilia", "few")

    ser.listen()
