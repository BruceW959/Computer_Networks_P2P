import threading

from Project_P2P.Proxy import Proxy
import hashlib


class PClient:
    block_size = 8192
    address = '127.0.0.1'
    stop_share = 0

    def __init__(self, tracker_addr: (str, int), proxy=None, port=None, upload_rate=0, download_rate=0):
        if proxy:
            self.proxy = proxy
        else:
            self.proxy = Proxy(upload_rate, download_rate, port)  # Do not modify this line!
        self.tracker = tracker_addr
        self.fileMap = {}  # hashmap: filename - list[section1, section2,...]
        self.threadList = []
        # register, register1, download1,  download2, download3, cancel
        self.info_batch = {'register': "", 'register1': "", "download1": "",
                           "download2": "", "download3": "", "cancel": "", "close": ""}
        #  self.share_batch = []
        self.thread = myThread(1, "Listen-1", self)
        self.thread.start()

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
                self.fileMap[fid].append(section)
                section = f.read(self.block_size)
        data = "200 OK;POST;register;" + str(fid) + "," + str(len(self.fileMap[fid]))
        print("load file successfully")
        while True:
            self.__send__(data.encode(), self.tracker)
            get_rev = ""
            while get_rev == "":
                get_rev = self.info_batch["register"]
            self.info_batch["register"] = ""
            if get_rev == '200 OK':
                break
        print("register success")
        return fid

    def register1(self, fid):
        data = "200 OK;POST;register1;" + str(fid) + "," + str(0)
        while True:
            self.__send__(data.encode(), self.tracker)
            get_rev = ""
            while get_rev == "":
                get_rev = self.info_batch["register1"]
            get_rev = get_rev.split(";")
            self.info_batch["register1"] = ""
            if get_rev[0] == '200 OK':
                data_size = int(get_rev[1])
                self.fileMap[fid] = [data_size]
                print("register1 success! " + get_rev[1])
                break

    def download(self, fid) -> bytes:
        """
        Download a file from P2P network using its unique identification
        :param fid: the unique identification of the expected file, should be the same type of the return value of register()
        :return: the whole received file in bytes
        """
        print("download function work")
        self.register1(fid)
        ready_download_list_index = [i for i in range(self.fileMap[fid][0])]
        self.fileMap[fid].pop(0)
        while ready_download_list_index:
            ready_index = ready_download_list_index.pop(0)
            ready_port = self.download1(fid, ready_index)
            get_session_data = self.download2(fid, ready_index, ready_port)
            print("get_se")
            if get_session_data:
                self.fileMap[fid].insert(ready_index, get_session_data)
                self.download3(fid, ready_index)
            else:
                ready_download_list_index.append(ready_index)
        data = b""
        print(len(self.fileMap[fid]))
        for i in self.fileMap[fid]:
            data += i
        return data

    def download1(self, fid, block_No):
        data = "200 OK;POST;download1;" + str(fid) + "," + str(block_No)
        while True:
            self.__send__(data.encode(), self.tracker)
            get_rev = ""
            while get_rev == "":
                get_rev = self.info_batch["download1"]
            self.info_batch["download1"] = ""
            get_rev = get_rev.split(";")
            if get_rev[0] == '200 OK':
                port = tuple(eval(get_rev[1]))[1]
                print("download1: get port" + str(port))
                return port

    def download2(self, fid, block_No, port):
        data = "share:" + str(fid) + "," + str(block_No)
        while True:
            self.__send__(data.encode(), (self.address, port))
            get_rev = ""
            while get_rev == "":
                get_rev = self.info_batch["download2"]
            self.info_batch["download2"] = ""
            session_data = get_rev
            print("download2: get session data")
            return session_data


    def download3(self, fid, block_No):
        data = "200 OK;POST;download3;" + str(fid) + "," + str(block_No)
        while True:
            self.__send__(data.encode(), self.tracker)
            get_rev = ""
            while get_rev == "":
                get_rev = self.info_batch["download3"]
            self.info_batch["download3"] = ""
            get_rev = get_rev.split(";")
            if get_rev[0] == '200 OK':
                print("download3: update process success")
                break

    def share(self, info, address):
            request_list = info.split(",")
            fid = request_list[0]
            block_No = int(request_list[1])
            if self.fileMap.get(fid) is not None and self.fileMap[fid][block_No] != 0:
                print("share start one, fid:" + fid + " block_No:" + str(block_No))
                data = 'download2:'.encode() + self.fileMap[fid][block_No]
                self.__send__(data, address)

    def cancel(self, fid):
        """
        Stop sharing a specific file, others should be unable to get this file from this client any more
        :param fid: the unique identification of the file to be canceled register on the Tracker
        :return: You can design as your need
        """
        if self.fileMap.get(fid) is not None:
            self.cancel1(fid)
            del self.fileMap[fid]


    def close(self):
        """
        Completely stop the client, this client will be unable to share or download files any more
        :return: You can design as your need
        """
        self.cancel2()
        print("emmm")
        self.thread.join()
        print("hahhah")


    def cancel1(self, fid):
        """
        给tracker 告知当前我已经cancel了固定的fid
        :return:
        """
        data = "200 OK;POST;cancel;" + str(fid)
        while True:
            self.__send__(data.encode(), self.tracker)
            get_rev = ""
            while get_rev == "":
                get_rev = self.info_batch["cancel"]
            self.info_batch["cancel"] = ""
            print(get_rev)
            if get_rev == '200 OK':
                return

    def cancel2(self):
        """
        给tracker 告知当前我已经全部cancel了
        :return:
        """
        data = "200 OK;POST;close;"
        while True:
            self.__send__(data.encode(), self.tracker)
            get_rev = ""
            while get_rev == "":
                get_rev = self.info_batch["close"]
            self.info_batch["close"] = ""
            if get_rev == '200 OK':
                return


"""
register, register1, download1,  download2, download3, cancel
        self.info_batch = ["" for i in range(6)]
        self.share_batch = []
"""
"""
                 if data_head == 'register':
            print("call function register()")
            pclient.info_batch

        elif data_head == 'register1':
            print("call function register1()")
            pclient.register1(data)

        elif data_head == "download1":
            print("call function download1()")
            pclient.download1(data)

        elif data_head == "download2":
            print("call function download2()")
            pclient.download2(data)
        elif data_head == "download3":
            print("call function download3")
            pclient.download3(data)
        elif data_head == "cancel":
            # Client can use this file to cancel the share of a file
            print("call function cancel()s")
            pclient.cancle(data)

         """


def listen(pclient):
    while True:
        info = pclient.__recv__()
        # print("listen " + info[0].decode() + str(info[1]))
        address = info[1]
        data = info[0]
        data_head, a, data_body = data.partition(b':')
        data_head = data_head.decode()
        print("listen " + data_head)
        # print("data_head:" + data_head + ",data_body:" + data_body)
        if data_head == 'share':
            pclient.share(data_body.decode(), address)
        else:
            if pclient.info_batch.get(data_head) is not None:
                if data_head == 'download2':
                   pclient.info_batch[data_head] = data_body
                else:
                    pclient.info_batch[data_head] = data_body.decode()
                    if data_head == 'close':
                        break


class myThread(threading.Thread):
    def __init__(self, threadID, name, pclient):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.pclient = pclient

    def run(self):
        print("开启多线程： " + self.name)
        listen(self.pclient)
        print("退出多线程： " + self.name)


