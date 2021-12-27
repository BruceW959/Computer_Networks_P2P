import threading

from Proxy import Proxy
import hashlib


class PClient:
    block_size = 2048
    address = '127.0.0.1'
    stop_share = 0

    def __init__(self, tracker_addr: (str, int), proxy=None, port=None, upload_rate=0, download_rate=0):
        if proxy:
            self.proxy = proxy
        else:
            self.proxy = Proxy(upload_rate, download_rate, port)  # Do not modify this line!
        self.tracker = tracker_addr
        self.fileMap = {}  # hashmap: filename - list[section1, section2,...]
        self.threadList=[]

    def __send__(self, data: bytes, dst: (str, int)):
        """
        Do not modify this function!!!
        You must send all your packet by this function!!!
        :param data: The data to be send
        :param dst: The address of the destination
        """
        self.proxy.sendto(data, dst)

    def __recv__(self, timeout=None) -> (bytes, (str, int)):
        """
        Do not modify this function!!!
        You must receive all data from this function!!!
        :param timeout: if its value has been set, it can raise a TimeoutError;
                        else it will keep waiting until receive a packet from others
        :return: a tuple x with packet data in x[0] and the source address(ip, port) in x[1]
        """
        return self.proxy.recvfrom(timeout)

    def register(self, file_path: str):
        """
        Share a file in P2P network
        :param file_path: The path to be shared, such as "./alice.txt"
        :return: fid, which is a unique identification of the shared file and can be used by other PClients to
                 download this file, such as a hash code of it
        """
        fid = hashlib.md5(file_path.encode()).hexdigest()
        """
        from the file_path read the file into memory
        """
        self.fileMap[fid] = []
        with open(file_path, 'rb') as f:
            section = f.read(self.block_size)
            while section:
                self.fileMap[fid].append([section])
                section = f.read(self.block_size)
        data = "200 OK;POST;register;" + str(fid) + "," + str(len(self.fileMap[fid]))
        while True:
            self.__send__(data.encode(), self.tracker)
            get_rev = self.__recv__()[0].decode().split(";")
            if get_rev[0] == '200 OK':
                break
        thread = myThread(1, "Share-1", self)
        thread.start()
        self.threadList.append((thread, fid))
        return fid

    def register1(self, fid):
        data = "200 OK;POST;register1;" + str(fid) + "," + str(0)
        while True:
            self.__send__(data.encode(), self.tracker)
            get_rev = self.__recv__()[0].decode().split(";")
            if get_rev[0] == '200 OK':
                data_size = int(get_rev[1])
                self.fileMap[fid] = [0 for _ in range(data_size)]
                break
        thread = myThread(1, "Share-2", self)
        thread.start()
        self.threadList.append((thread, fid))

    def download(self, fid) -> bytes:
        """
        Download a file from P2P network using its unique identification
        :param fid: the unique identification of the expected file, should be the same type of the return value of register()
        :return: the whole received file in bytes
        """
        self.register1(fid)
        ready_download_list_index = []
        index = 0
        for i in self.fileMap[fid]:
            if i == 0:
                ready_download_list_index.append(index)
            index += 1
        while ready_download_list_index:
            ready_index = ready_download_list_index.pop(0)
            ready_port = self.download1(fid, ready_index)
            get_session_data = self.download2(fid, ready_index, ready_port)
            if get_session_data:
                self.fileMap[fid].insert(ready_index, get_session_data)
                self.download3(fid,ready_index)
            else:
                ready_download_list_index.append(ready_index)
        data = ""
        for i in self.fileMap[fid]:
            data += i
        return data.encode()

    def download1(self, fid, block_No):
        data = "200 OK;POST;download1;" + str(fid) + "," + str(block_No)
        while True:
            self.__send__(data.encode(), self.tracker)
            get_rev = self.__recv__()[0].decode().split(";")
            if get_rev[0] == '200 OK':
                port = int(get_rev[1])
                return port

    def download2(self, fid, block_No, port):
        data = "200 OK;POST;download2;" + str(fid) + "," + str(block_No)
        while True:
            self.__send__(data.encode(), (self.address, port))
            get_rev = self.__recv__()[0].decode().split(";")
            if get_rev[0] == '200 OK':
                session_data = get_rev[1]
                return session_data

    def download3(self, fid, block_No):
        data = "200 OK;POST;download3;" + str(fid) + "," + str(block_No)
        while True:
            self.__send__(data.encode(), self.tracker)
            get_rev = self.__recv__()[0].decode().split(";")
            if get_rev[0] == '200 OK':
                break

    def cancel(self, fid):
        """
        Stop sharing a specific file, others should be unable to get this file from this client any more
        :param fid: the unique identification of the file to be canceled register on the Tracker
        :return: You can design as your need
        """
        for i in self.threadList:
            if i[1] == fid:
                i[0].join()
                self.cancel1(fid)

    def close(self):
        """
        Completely stop the client, this client will be unable to share or download files any more
        :return: You can design as your need
        """
        for i in self.threadList:
            i[0].join()
        self.cancel2()
        self.proxy.close()

    def cancel1(self, fid):
        """
        给tracker 告知当前我已经cancel了固定的fid
        :return:
        """
        data = "200 OK;POST;cancel1;" + str(fid)
        while True:
            self.__send__(data.encode(), self.tracker)
            get_rev = self.__recv__()[0].decode().split(";")
            if get_rev[0] == '200 OK':
                return

    def cancel2(self):
        """
        给tracker 告知当前我已经全部cancel了
        :return:
        """
        data = "200 OK;POST;cancel2;"
        while True:
            self.__send__(data.encode(), self.tracker)
            get_rev = self.__recv__()[0].decode().split(";")
            if get_rev[0] == '200 OK':
                return


def share(pclient):
    while True:
        info = pclient.__recv__()
        print(info)#.decode()
        request_addr = info[1]
        request_list = info[0].split(";")
        if request_list[2] == 'download2':
            fid = request_list[3].split(",")[0]
            block_No = int(request_list[3].split(",")[1])
            data = '200 OK;' + pclient.fileMap[fid][block_No]
            pclient.__send__(data.encode(), request_addr)
            break


class myThread(threading.Thread):
    def __init__(self, threadID, name, pclient):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.pclient = pclient

    def run(self):
        print("开启多线程： " + self.name)
        share(self.pclient)
        print("退出多线程： " + self.name)
