from socketserver import BaseRequestHandler, ThreadingUDPServer
from Proxy import Proxy
import numpy as np
import random


class Tracker:
    def __init__(self, upload_rate=10000, download_rate=10000, port=None):
        self.proxy = Proxy(upload_rate, download_rate, port)
        self.files = {}
        self.clients = {}  # format of key: (fid,index_of_block)

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


        # update self.files
        if fid in self.files:
            # has registered before:update
            for i in range(number_of_blocks):
                if i in self.files[fid]:  # has the block
                    if client not in self.files[fid][i]:
                        self.files[fid][i].append(client)
                else:  # doesn't have the block
                    self.files[fid][i] = [client]
        else:  # first time for the file
            self.files[fid] = {}
            for i in range(number_of_blocks):
                self.files[fid][i] = [client]


        # update size record
        if "size" not in self.files[fid]:
            self.files[fid]['size'] = number_of_blocks

        # update self.clients
        if client not in self.clients:  # first time for the client
            self.clients[client] = [fid]
        else:  # client has registered
            if fid not in self.clients[client]:  # first time for the file for the client
                self.clients[client].append(fid)

        print("register success! client:", client, "fid: ", fid)
        self.response("register:200 OK", frm)

    def query(self, info, frm: (str, int)):
        fid = info.split(',')[0]
        query_indexes = info.split(',')[1].split('_')
        query_indexes = [int(i) for i in query_indexes]
        result = []
        if fid not in self.files:
            self.response("download1:404 NOT FOUND", frm)
            print("query finished: not found")
        else:
            has_one = False
            for query_index in query_indexes:
                if query_index in self.files[fid] and len(self.files[fid]) > 0:
                    has_one = True
                    tmp = self.files[fid][query_index].pop(0)
                    self.files[fid][query_index].append(tmp)
                    result.append("%d-" + tmp % query_index)
            if not has_one:
                self.response("download1:404 NOT FOUND", frm)
                print("query finished: not found")
            else:
                tmp='_'.join(result)
                self.response("download1:200 OK;" + tmp, frm)
                print("query finished: "+tmp)

        # if (fid,query_index) not in self.downloading_ques:
        #     index=0
        #     self.downloading_ques[(fid,query_index)]=(index,[])
        #     clients=list(self.files[fid].keys())
        #     for c in clients:
        #         if query_index in self.files[fid][c]:
        #
        # for c in self.files[fid]:
        #     result.append(c)
        # self.response("[%s]" % (", ".join(result)), frm)

    def cancel(self, info, frm: (), client):
        fid = info
        size = self.files[fid]['size']
        for i in range(size):
            if client in self.files[fid][i]:
                self.files[fid][i].remove(client)
        if fid in self.clients[client]:
            self.clients[client].remove(fid)
        self.response("cancel:200 OK", frm)

    def register1(self, info, frm):  # query for the size of the file
        fid = info.split(',')[0]
        if fid not in self.files \
                or 'size' not in self.files[fid]:
            self.response("register1:404 NOT FOUND", frm)
            print("register1 fail")
        else:
            self.response("register1:200 OK;%d" % self.files[fid]['size'], frm)
            print("register1 success! No.of blocks: ", self.files[fid]['size'])

    def instant_register(self, info, frm: (str, int), client):
        fid = info.split(',')[0]
        indexes = info.split(',')[1].split('_')
        indexes = [int(i) for i in indexes]
        # update self.files
        for index in indexes:
            if client not in self.files[fid][index]:
                self.files[fid][index].append(client)


        # update self.clients
        if client not in self.clients:
            self.clients[client] = [fid]
        elif fid not in self.clients[client]:
            self.clients[client].append(fid)
        print("instant register success")
        self.response("download3:200 OK", frm)

    def start(self):
        while True:
            msg, frm = self.__recv__()
            msg, client = msg.decode(), "(\"%s\", %d)" % frm
            method = msg.split(';')[2]
            info = msg.split(';')[3]
            print("receive success!", "request: ", method, "info: ", info)

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

            elif method == "download1":
                # Client can use this to who has the specific file with the given fid
                # fid = msg[6:]
                print("call function query()")
                self.query(info, frm)

            elif method == "cancel":
                # Client can use this file to cancel the share of a file
                print("call function cancel()s")
                self.cancel(info, frm, client)

            elif method == "close":
                self.response("close:200 OK", frm)


if __name__ == '__main__':
    tracker = Tracker(port=10086)
    tracker.start()
