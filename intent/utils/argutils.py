"""
Created on Aug 26, 2013

:author: rgeorgi
"""
from glob import glob
import sys
import os
import argparse


from .ConfigFile import ConfigFile


def require_opt(option, msg, must_exist=False, must_exist_msg='The file "%s" was not found\n'):
    errors = False
    if not option:
        sys.stderr.write('ERROR: %s\n' % msg)
        errors = True
    elif must_exist and not os.path.exists(option):
        sys.stderr.write('ERROR: ' + must_exist_msg % option)
        errors = True
    return errors


# ===============================================================================
# Exceptions
# ===============================================================================
class CommandLineException(Exception):
    pass


class PathArgException(CommandLineException): pass


class PathNotExistsException(PathArgException): pass


class PathInvalidException(PathArgException): pass


# ===============================================================================
# Argparse Types
# ===============================================================================

def exists(path):
    """
    Type for passing to argparse to verify that the argument is an extant path.
    """
    if not os.path.exists(path):
        raise CommandLineException('Path "%s" does not exist' % path)
    else:
        return path


def existsfile(path):
    """
    Type for passing to argparse to verify that the argument both:

    - Is a file
    - Exists on the filesystem
    """
    if not os.path.exists(path):
        raise PathNotExistsException('File "%s" does not exist.' % path)
    elif not os.path.isfile(path):
        raise PathInvalidException('Path "%s" is not a file.' % path)
    else:
        return path


def existsdir(path, rootpath=None):
    '''
    Type for passing to argparse to verify that the argument both:

    - Is a directory
    - Exists on the filesystem

    :param path: Path to check
    :param rootpath: Path from which to construct relative paths.
    '''
    if not os.path.isabs(path) and rootpath:
        path = os.path.join(rootpath, path)

    if not os.path.exists(path):
        raise PathNotExistsException('Directory "%s" does not exist.' % path)
    if not os.path.isdir(path):
        raise PathInvalidException('Path "%s" is not a directory.' % path)
    else:
        return path


def configfile(path):
    c = existsfile(path)
    return ConfigFile(c)


def writedir(path):
    os.makedirs(path, exist_ok=True)
    return path


def writefile(path, mode='w', encoding='utf-8'):
    """
    Ensure that this file is writable in the given path, and return it as an
    open file object.

    :param path: Path to the file to write
    :type path: filepath
    :param mode: Write mode
    :type mode: [ 'w' | 'wb' ]
    :param encoding: File encoding
    :type encoding: encoding
    """
    dir = os.path.dirname(path)

    if dir and not os.path.exists(dir):
        os.makedirs(dir, exist_ok=True)

    try:
        f = open(path, mode, encoding=encoding)
    except Exception as e:
        raise e

    return f

def csv_choices(choice_list):

    def in_choices(x):

        ret_list = []
        if not choice_list:
            return []

        for t in x.split(','):
            if t.lower() not in choice_list:
                raise argparse.ArgumentError('Argument "{}" is an invalid choice. Valid choices are: {}'.format(t, choice_list))
            else:
                ret_list.append(t)

        return ret_list

    return in_choices

def globfiles(file_arg):
    return glob(file_arg)

def proportion(arg):
    try:
        float(arg)
    except Exception as e:
        raise argparse.ArgumentError("Invalid format for proportion: {}".format(arg))

    p = float(arg)
    if p < 0 or p > 1.0:
        raise argparse.ArgumentError('Proportion arguments should be between 0 and 1.0. Argument "{}" is invalid.'.format(p))

    return p

# ===============================================================================
# Default to showing help for an argparser
# ===============================================================================

class DefaultHelpParser(argparse.ArgumentParser):
    """
    Make the argparser default to printing help when an error is encountered.
    """

    def error(self, message):
        sys.stderr.write('error: %s\n\n' % message)
        self.print_help()
        sys.exit(2)

    def convert_arg_line_to_args(self, arg_line):
        if arg_line.startswith('#') or not arg_line.strip():
            return
        else:
            for arg in arg_line.split():
                yield arg