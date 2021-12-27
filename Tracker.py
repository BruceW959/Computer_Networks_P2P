from socketserver import BaseRequestHandler, ThreadingUDPServer
from Proxy import Proxy
import numpy as np
import random


class Tracker:
    def __init__(self, upload_rate=10000, download_rate=10000, port=None):
        self.proxy = Proxy(upload_rate, download_rate, port)
        self.files = {}
        self.size_record = {}
        self.downloading_ques = {}  # format of key: (fid,index_of_block)

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

    def response(self, data: str, address: (str, int)):
        self.__send__(data.encode(), address)

    # "200 OK;XXXX;register;{fid},int"
    def register(self, info, frm: (str, int), client):
        fid = info.split(',')[0]
        number_of_blocks = info.split(',')[1]
        number_of_blocks = int(number_of_blocks)
        if fid in self.files:
            # has registered before: update
            tmp = [i + 1 for i in range(number_of_blocks)]
            self.files[fid][client] = np.unique(self.files[fid][client] + tmp).tolist()
        else:
            # hasn't registered before
            self.size_record[fid] = number_of_blocks  # record the No. of blocks of the file
            self.files[fid] = {}
            self.files[fid][client] = [i + 1 for i in range(number_of_blocks)]
        print("register success! client:",client,"fid: ",fid)
        self.response("200 OK", frm)

    def query(self, info, frm: (str, int)):
        fid = info.split(',')[0]
        query_index = info.split(',')[1]
        query_index = int(query_index)+1
        result = []
        if fid not in self.files:
            self.response("404 NOT FOUND", frm)
            print("query finished: not found")
        else:
            clients = list(self.files[fid].keys())
            for c in clients:
                if query_index in self.files[fid][c]:
                    result.append(c)
            self.response("200 OK;".join(result[random.randint(0, len(result) - 1)]), frm)
            print("query finished: candidate_list: ",result)

        # if (fid,query_index) not in self.downloading_ques:
        #     index=0
        #     self.downloading_ques[(fid,query_index)]=(index,[])
        #     clients=list(self.files[fid].keys())
        #     for c in clients:
        #         if query_index in self.files[fid][c]:
        #
        # for c in self.files[fid]:
        #     result.append(c)
        #self.response("[%s]" % (", ".join(result)), frm)

    def cancel(self, info, frm: (), client):
        fid = info.split(',')[0]
        file_list = list(self.files.keys())
        for fid in file_list:
            del self.files[fid][client]
        self.response("Success", frm)

    def register1(self, info, frm):  # query for the size of the file
        fid = info.split(',')[0]
        tmp=list(self.size_record.keys())
        if fid in tmp:
            self.response("200 OK;%d" % self.size_record[fid], frm)
            print("register1 success! No.of blocks: ", self.size_record[fid])
        else:
            self.response("404 NOT FOUND", frm)
            print("register1 fail")


    def instant_register(self, info, frm: (str, int), client):
        fid = info.split(',')[0]
        index = info.split(',')[1]
        if client in self.files[fid]:  # this client has registered for other blocks of the same file
            self.files[fid][client].append(index)
            self.files[fid][client] = np.unique(self.files[fid][client]).tolist()
        else:  # register the file for the first time
            self.files[fid][client] = [index]
        print("instant register success", self.files[fid][client])
        self.response("200 OK",frm)

    def start(self):
        while True:
            msg, frm = self.__recv__()
            msg, client = msg.decode(), "(\"%s\", %d)" % frm
            method = msg.split(';')[2]
            info = msg.split(';')[3]
            print("receive success!","request: ",method,"info: ",info)

            if method == 'register':
                # Client can use this to REGISTER a file and record it on the tracker
                # fid = msg[9:]
                print("call function register()")
                self.register(info, frm, client)

            elif method == 'register1':
                print("call function register1()")
                self.register1(info, frm)

            elif method == "download3":
                print("call function instant_register()")
                self.instant_register(info, frm, client)

            elif method=="download1":
                # Client can use this to who has the specific file with the given fid
                # fid = msg[6:]
                print("call function query()")
                self.query(info, frm)

            elif method == "cancel":
                # Client can use this file to cancel the share of a file
                print("call function cancel()s")
                self.cancel(info, frm, client)


if __name__ == '__main__':
    tracker = Tracker(port=10086)
    tracker.start()
