from hashlib import md5
from os.path import join, isfile, getmtime, getsize, split, exists
from os import listdir, makedirs

def mkqueue(list,q):
    """
    The function used to put tasks in the DownloadQueue

    :param list: The list containing the file information used to generate the DownloadQueue, that is the download list
    :param q: DownloadQueue
    :return: No return value
    """
    for i in list:
        q.put(i)

def get_file_md5(filepath):
    """
    The function for detecting the md5 value of a file

    :param filepath: The file path of this file
    :return: The md5 value of this file
    """
    global file_dir
    f = open(filepath, 'rb')
    contents = f.read()
    f.close()
    return md5(contents).hexdigest()

def traverse(dir_path):
    """
    Recursively iterates through all the files in the specified path and generates a list to store the file list information.

    :param dir_path: The path to be traversed
    :return:
    """
    file_list = [] # only path
    file_folder_list = listdir(dir_path)
    for file_folder_name in file_folder_list:
        if isfile(join(dir_path, file_folder_name)):
            tem = join(dir_path, file_folder_name)[-5:]
            if tem != '.temp':
                # print(join(dir_path, file_folder_name))
                # print('--------Not a temp file---------')
                file_list.append(join(dir_path, file_folder_name))
        else:
            file_list.extend(traverse(join(dir_path, file_folder_name)))
    print('file_list size',len(file_list))
    return file_list

def mkdirs(file_path):
    """
    Recursively create the folder if it does not exist

    :param file_path:
    :return:
    """
    (filepath, tempfilename) = split(file_path)
    # print(filepath)
    # print(tempfilename)
    isExists=exists(filepath)
    if not isExists:
        makedirs(filepath, exist_ok=True)
        return True
    # if it exists, it is not created
    else:
        return False

def mkfilelist(dir_path):
    """
    Recursively scans all the files in the specified folder and generates a list containing the path, mtime, and size of each file, corresponding to three sublists.
    The structure of the list is [[file_path],[mtime],[file-size]]

    :param dir_path:
    :return: file list
    """
    file_path_list = traverse(dir_path)
    mtime = []
    filesize =[]
    for i in file_path_list:
        try:
            file_size = getsize(i)
            m_time = getmtime(i)
            filesize.append(file_size)
            mtime.append(m_time)
        except FileNotFoundError:
            print('file not found')
            pass
    filelist = [file_path_list, mtime, filesize]
    return filelist

# make download task flag = 1
def mktask(locallist, remotelist):
    """
    Generate a list of download tasks based on the local file list and the remote file list. Each element of the list is a dictionary containing all information about a file.

    :param locallist: The local file list
    :param remotelist: The remote file list
    :return: download list
    """
    list = []
    diflist = set(locallist[0]) ^ set(remotelist[0])
    print(diflist)
    for i in diflist:
        for j in range(len(remotelist[0])):
            if i == remotelist[0][j]:
                temp ={
                    'flag': 1,
                    'file_path': remotelist[0][j],
                    'mtime': remotelist[1][j],
                    'file_size': remotelist[2][j],
                }
                list.append(temp)
    return list
# make update task flag = 0
def mkupdatetask(remotedatabase, remotelist):
    """
    Generate a list of tasks to be updated based on the remotedatabase and the remotelist
    :param remotedatabase: RemoteDatabase stored locally, which is a list of files already synchronized with the remote PC
    :param remotelist: The latest remote list sent by the remote PC
    :return: update list
    """
    list = []
    for i in range(len(remotedatabase[0])):
        for j in range(len(remotelist[0])):
            if remotedatabase[0][i] == remotelist[0][j]:
                if remotedatabase[1][i] < remotelist[1][j]:
                    temp = {
                        'flag': 0,
                        'file_path': remotelist[0][j],
                        'mtime': remotelist[1][j],
                        'file_size': remotelist[2][j],
                    }
                    list.append(temp)
    return list

def updateRemoteDatabase(remotedatabase, header_dic):
    """
    Update the RemoteDatabase based on the header of the file
    :param remotedatabase: RemoteDatabase stored locally
    :param header_dic: A dictionary containing information about a simple file
    :return: Updated RemoteDatabase
    """

    file_path = header_dic['file_path']
    mtime = header_dic['mtime']
    file_size = header_dic['file_size']
    flag = 0
    for i in range(len(remotedatabase[0])):
        if remotedatabase[0][i] == file_path:
            if remotedatabase[1][i] < mtime:
                remotedatabase[1][i] = mtime
                remotedatabase[2][i] = file_size
                print('-'*10 ,file_path,' update!!','-'*10)
                flag = 1
                return remotedatabase
    if flag == 0:
        remotedatabase[0].append(file_path)
        remotedatabase[1].append(mtime)
        remotedatabase[2].append(file_size)
    return remotedatabase

