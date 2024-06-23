from queue import Queue
from threading import Thread, Lock
from os import path, mkdir
from argparse import ArgumentParser
import filelist as fl
import filetransfer as ft

# Initialize global variables
LocalIp = '0.0.0.0'
RemoteIp = ''
FLport = 20000
Fport = 25000
BUFFER_SIZE = 1024*1024
DownloadQueue = Queue()
RemoteDatabase = [[],[],[]]
Lock = Lock()

def _argparse():
    parser = ArgumentParser(description="This is a description!")
    parser.add_argument('--ip', action='store', required=True, dest='ip', help='IP address')
    return parser.parse_args()

def ip_address():
    parser = _argparse()
    global RemoteIp
    RemoteIp = parser.ip

if __name__ =="__main__":
    # Accept parameters
    ip_address()
    folder_name = 'share'
    isExists = path.exists(folder_name)
    if not isExists:
        mkdir(folder_name)
    while True:
        print('LocalIp: ', LocalIp)
        print('RemoteIp: ', RemoteIp)
        t1 = Thread(target=ft.FileServer, args=(LocalIp, Fport, BUFFER_SIZE,))
        t2 = Thread(target=fl.SendFilelistTh, args=(LocalIp, RemoteIp ,FLport,))
        t3 = Thread(target=fl.RecvFilelistTh, args=(RemoteIp ,FLport, Fport, BUFFER_SIZE, DownloadQueue, Lock,))
        t1.start()
        t2.start()
        t3.start()
        t1.join()
        t2.join()
        t3.join()


