"""
Created on Oct 24, 2013

@author: rgeorgi
"""
import os, re, glob

def lc(fname):
    """
    Get the linecount for a file.
    :param fname:
    """
    with open(fname, encoding='utf-8') as f:
        i = 0
        for i, l in enumerate(f):
            pass
        return i + 1

def makedirs(path):
    if path.strip():
        os.makedirs(path, exist_ok=True)


def swapext(path, ext):
    """
    Swap the extension on a file

    :param path: Path to the file
    :type path: filepath
    :param ext: new extension (if not starting with "." one will be added)
    :type ext: str
    """
    return os.path.splitext(path)[0]+ext

def remove_safe(path):
    if os.path.exists(path):
        os.remove(path)

def dir_above(path, n=1):
    while n>0:
        path = os.path.dirname(path)
        n -=1
    return path

def matching_files(dirpath, pattern, recursive=False):
    """
    Return the paths matching a pattern in a directory, optionally recurse
    into the subdirectories.

    @param dirpath: directory to scan
    @param pattern: regular expression to match paths upon
    @param recursive: whether or not to recurse into the directories.
    """

    # Get absolute paths for all the current files.
    paths = [os.path.join(dirpath, p) for p in os.listdir(dirpath)]

    # Find all the matching paths in the directory.
    files = [f for f in paths if os.path.isfile(f) and re.match(pattern, os.path.basename(f))]


    dirs = [d for d in paths if os.path.isdir(d)]




    if recursive:
        for dir in dirs:
            files.extend(matching_files(dir, pattern, recursive))

    return files

def globlist(globlist):
    retlist = []
    for globpattern in globlist:
        retlist.extend(glob.glob(globpattern))
    return retlist