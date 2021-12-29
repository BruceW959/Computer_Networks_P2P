import time
from threading import Thread

from PClient import PClient

tracker_address = ("127.0.0.1", 10086)

if __name__ == '__main__':
    # A,B,C,D,E join the network
    A = PClient(tracker_address, upload_rate=100000, download_rate=70000)
    B = PClient(tracker_address, upload_rate=50000, download_rate=70000)
    C = PClient(tracker_address, upload_rate=150000, download_rate=60000)
    D = PClient(tracker_address, upload_rate=25000, download_rate=100000)
    E = PClient(tracker_address, upload_rate=20000, download_rate=10000)
    F = PClient(tracker_address, upload_rate=50000, download_rate=100000)

    clients = [B, C, D]
    # A register a file and B download it
    fid = A.register("../test_files/alice.txt")
    threads = []
    files = {}
    newAdd=[]

    # function for download and save
    def download(node, index):
        files[index] = node.download(fid)


    time_start = time.time_ns()
    for i, client in enumerate(clients):
        threads.append(Thread(target=download, args=(client, i)))
    # start download in parallel
    for t in threads:
        t.start()
    # wait for finish
    for t in threads:
        if t == C:
            time.sleep(10)
            C.close()# C exits
            clients = [E, F]
            for i, client in enumerate(clients):
                newAdd.append(Thread(target=download, args=(client, i)))
            for t1 in newAdd:
                t1.start()
    for t in threads:
        t.join()
    # check the downloaded files
    with open("../test_files/alice.txt", "rb") as bg:
        bs = bg.read()
        for i in files:
            if files[i] != bs:
                raise Exception("Downloaded file is different with the original one")

    # B, C, D, E has completed the download of file
    threads.clear()



    A.close()
    B.close()
    D.close()
    E.close()
    F.close()
    print("Good job")
# when downloading,one node exit while another 3 nodes join in downloading