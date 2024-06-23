from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from struct import pack, unpack
from json import dumps, loads
from threading import Thread
from tqdm import tqdm
from os import path, remove, rename
import function as func
from main import RemoteDatabase

# send files
def FileServer(localip, fport, buffer_size):
    """
    This thread is used to listen and accept file download requests and start file transfers

    :param localip: The ip address for the local host
    :param fport: The port used for receive file from remote host
    :param buffer_size: The size of each socket buffer
    :return: No return value
    """
    fileserver = socket(AF_INET, SOCK_STREAM)
    fileserver.setsockopt(SOL_SOCKET, SO_REUSEADDR,1)
    fileserver.bind((localip, fport))
    #
    fileserver.listen(10)
    while True:
        conn, recv_socket_addr = fileserver.accept()
        try:
            t = Thread(target=SendFilePro, args=(conn, recv_socket_addr, buffer_size,))
            t.start()
        except Exception as E:
            pass

def RecvFilePro(dq, remoteip, fport, buffer_size, lock):
    """
    Send a download request to a remote host and receive the file
    :param dq: The pointer of the DownloadQueue
    :param remoteip: The ip address for the remote host
    :param fport: The port used for receive file from remote host
    :param buffer_size: The size of each socket buffer
    :param lock: Thread lock for handling multi-threaded data conflicts
    :return: No return value
    """
    try:
        recv_socket = socket(AF_INET, SOCK_STREAM)
        recv_socket.connect((remoteip, fport))
        try:
            # flag = 1 download new
            # flag = 0 update file
            header_dic = dq.get()
            print('request for file')
            print('qsize = ', dq.qsize())

            FLAG = header_dic['flag']
            file_path = header_dic['file_path']
            mtime = header_dic['mtime']
            total_size = header_dic['file_size']

            d = func.mkdirs(file_path)
            ext = ''
            if FLAG == 1:
                ext = '.temp'
            elif FLAG == 0:
                ext = '.upd'

            recved_size = 0
            if path.exists(file_path + '.temp'):
                recved_size = path.getsize(file_path + '.temp')
            # send header
            recved_block_num = int(recved_size // buffer_size)
            print(recved_block_num)
            header_dir = {
                'flag': FLAG,
                'file_path':file_path,
                'recv_block': recved_block_num,
                'file_size': total_size
            }
            header_json = dumps(header_dir)
            header_bytes = header_json.encode('utf-8')

            recv_socket.send(pack('i', len(header_bytes)))
            # recv_socket.send(struct.pack('g', len(header_bytes)))
            recv_socket.send(header_bytes)

            position = recved_block_num * buffer_size
            progress = tqdm(range(total_size), f"Receiving {file_path}", unit="B", unit_scale=True, unit_divisor=1024)
            # with open('%s\%s' %(download_dir,filename), 'wb') as f:
            with open(file_path + '.temp', 'ab') as f:
                f.seek(position)
                if position != 0:
                    progress.update(position)
                while True:
                    # read 1024 bytes from the socket (receive)
                    bytes_read = recv_socket.recv(buffer_size)
                    if not bytes_read:
                        break
                    f.write(bytes_read)
                    progress.update(len(bytes_read))
            # check file
            if func.getsize(file_path + '.temp') == total_size:
                print("SIZE check ok!")
                if FLAG == 1:
                    if path.exists(file_path):
                        remove(file_path)
                    rename(file_path + '.temp', file_path)
                    print(file_path, ' download success')
                    lock.acquire()
                    func.updateRemoteDatabase(RemoteDatabase, header_dic)
                    lock.release()
                elif FLAG == 0:
                    if path.exists(file_path):
                        # if func.getmtime(file_path) < mtime:
                        remove(file_path)
                        rename(file_path + '.temp', file_path)
                        print(file_path, ' update success')
                        lock.acquire()
                        func.updateRemoteDatabase(RemoteDatabase, header_dic)
                        lock.release()
            else:
                remove(file_path + '.temp')
                print(file_path, ' download fail')
                recv_socket.close()

        except ConnectionError:
            pass
            recv_socket.close()
    except Exception as E:
        pass

def SendFilePro(conn, recv_socket_addr, buffer_size):
    """
    Send a file to the remote host where the download request was confirmed
    :param conn: The pointer to the socket used to send the file
    :param recv_socket_addr: The address of the socket connected to the remote host
    :param buffer_size: The size of each socket buffer
    :return:  No return value
    """
    print('start file transfer to', recv_socket_addr)
    try:
        # recv header
        obj = conn.recv(4)
        header_size = unpack('i', obj)[0]

        header_bytes = conn.recv(header_size)
        header_json = header_bytes.decode('utf-8')
        header_dir = loads(header_json)
        print(header_dir)
        # flag = 1 means send file head

        if header_dir['flag'] == 1:
            print('send new file to', recv_socket_addr)
        elif header_dir['flag'] == 0:
            print('update file to', recv_socket_addr)
        else:
            print('------------------FLAG Error---------------------')
            conn.close()

        # header message
        file_path = header_dir['file_path']
        if file_path[-4:]=='.new':
            file_path = file_path[0:-4]
        # BUFFER_SIZE = 1024
        recved_block_num = int(header_dir['recv_block'])
        total_size = int(header_dir['file_size'])

        progress = tqdm(range(total_size), f"Sending {file_path}", unit="B", unit_scale=True, unit_divisor=1024)
        with open(file_path, 'rb') as f:
            new_position = recved_block_num * buffer_size
            print(new_position)
            f.seek(new_position)
            if new_position != 0:
                progress.update(new_position)
            while True:
                # read the bytes from the file
                bytes_read = f.read(buffer_size)
                if not bytes_read:
                    # file transmitting is done
                    break
                # we use sendall to assure transimission in
                # busy networks
                conn.sendall(bytes_read)
                # update the progress bar
                progress.update(len(bytes_read))
        conn.close()
        print("finish transfer")
    except Exception as E:
        # print(E)
        pass
        conn.close()
