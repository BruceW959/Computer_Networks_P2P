from threading import Thread

from PClient import PClient
from SC_model.client import Client
from SC_model.client import client_download
import time

tracker_address = ("127.0.0.1", 10086)

if __name__ == '__main__':
    # A,B join the network
    A = PClient(tracker_address, upload_rate=100000, download_rate=100000)
    B = PClient(tracker_address, upload_rate=100000, download_rate=100000)

    C = Client("c", 10000)
    D = Client("d", 10000)
    # A register a file and B download it
    fid = A.register("../test_files/bg.png")
    data1 = B.download(fid)
    threads = []


    def download(node, index):
        fid[index] = node.download(fid)


    def download1(cclient):
        client_download(cclient)


    Pclient = [A, B]
    clientt = [C, D]
    for i, cli in enumerate(Pclient):
        threads.append(Thread(target=download, args=(cli, i)))
    for i, cli in enumerate(clientt):
        threads.append(Thread(target=client_download, args=[cli]))

    time_start = time.time_ns()
    for t in threads:
        t.start()

    with open("../test_files/pg.png", "rb") as bg:
        bs = bg.read()
        for i in fid:
            if fid[i] != bs:
                raise Exception("Downloaded file is different with the original one")
    print((time.time_ns() - time_start) * 1e-9)

    A.close()
    B.close()
    C.proxy.close()
    D.proxy.close()
