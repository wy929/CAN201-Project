from concurrent.futures import ThreadPoolExecutor
from threading import Thread
from time import sleep
from json import dumps, loads
from struct import pack, unpack
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
import function as func
import filetransfer as ft
from main import RemoteDatabase

def SendFilelistTh(localip, remoteip, flport):
    """
    This thread is used to listen remote connections and send file list

    :param localip: The ip address for the local host
    :param remoteip: The ip address for the remote host
    :param flport: The port used for manage file list message
    :return: No return value
    """
    server = socket(AF_INET, SOCK_STREAM)
    server.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    server.bind((localip, flport))
    server.listen(5)
    print(localip,' is waiting for request from', remoteip)
    while True:
        try:
            # waiting for connection
            conn, client_addr = server.accept()
            print(conn, ' connected to ', client_addr)
            # receive flag
            obj = conn.recv(4)
            request = unpack('i', obj)[0]
            # insure request
            if request == 1: # flag = 1
                filelist = func.mkfilelist('share')
                print('---------------------------------------')
                print('start to send file list to', client_addr)
                print(filelist)
                print('---------------------------------------')
                filelist_json = dumps(filelist)
                filelist_bytes = filelist_json.encode('utf-8')
                # conn.send(struct.pack('i', len(filelist_bytes)))
                conn.sendall(filelist_bytes)
            else:
                conn.close()
                print('request error')
        except Exception as E:
            # conn.close()
            print('sendlist conn closed')
            pass


def RecvFilelistTh(remoteIp, flport, fport, buffer_size, dq, lock):
     """
     This thread is used to send file list requests and receive list information form the remote host

     :param remoteIp: The ip address for the remote host
     :param flport: The port used for manage file list message
     :param fport: The port used for receive file from remote host
     :param buffer_size: The size of each socket buffer
     :param dq: DownloadQueue for file downloads
     :param lock: Thread lock for handling multi-threaded data conflicts
     :return: No return value
     """
     while True:
        if dq.empty() is True:
            print('queue is empty, start new request to ', remoteIp, flport)
            # make local list
            local_list = func.mkfilelist('share')
            # database = local_list #####
            # print('-----------------','database',database,'------------------')
            t = Thread(target=RecvFilelistConn, args=(remoteIp, flport, fport, buffer_size, dq, lock,))
            t.start()
            t.join()
            sleep(10)
        else:
            print('qsize = ', dq.qsize())
            sleep(10)

def RecvFilelistConn(remoteip ,flport, fport, buffer_size, dq, lock):
    """
    This is a sub-thread of RecvFilelistTh, used to accept remote file lists and generate file download requests

    :param remoteip: The ip address for the remote host
    :param flport: The port used for manage file list message
    :param fport: The port used for receive file from remote host
    :param buffer_size: The size of each socket buffer
    :param dq: DownloadQueue for file downloads
    :param lock: Thread lock for handling multi-threaded data conflicts
    :return: No return value
    """
    connect = False
    # connect to remote
    recvfl_s = socket(AF_INET, SOCK_STREAM)
    try:
        if not connect:
            recvfl_s.connect((remoteip, flport))
            print('recvfl_s connect ok-------------')
            # send flag
            recvfl_s.send(pack('i', 1))
            list_bytes = recvfl_s.recv(20480)
            list_json = list_bytes.decode('utf-8')
            remote_list = loads(list_json)
            # print('remote filelist size from ', remoteip)
            # print('local_list', local_list)
            # print('remote_list', remote_list)
            # print('remotedatabase', remotedatabase)

            # make download list
            download_list = func.mktask(RemoteDatabase,remote_list)
            # print('download_list', download_list)
            func.mkqueue(download_list, dq)
            # make update list
            update_list = func.mkupdatetask(RemoteDatabase, remote_list)
            # print('update_list', update_list)
            func.mkqueue(update_list, dq)
            recvfl_s.close()
            print('recvfl_s closed')
            print('queue size = ', dq.qsize())
            downloadPool = ThreadPoolExecutor(5)
            while True:
                if dq.empty() is True:
                    break
                downloadPool.submit(ft.RecvFilePro(dq, remoteip, fport, buffer_size, lock))
            print('-----------------------download_list completed---------------------------------')
    except Exception as E:
        connect = False
        recvfl_s.close()





