import re
import os
import time
import inspect
import logging
import tempfile
import subprocess
import configparser


class TASK_RUNNING(Exception):
    pass


def git_root():
    res = subprocess.run(["git","rev-parse","--show-toplevel"],
                         stdout=subprocess.PIPE).\
                         stdout.decode().split('\n')[0]
    return res


def if_in_celery():
    from open_elevation.celery_tasks \
        import CELERY_APP
    if not CELERY_APP.current_worker_task:
        return False
    return True


def list_files(path, regex):
    r = re.compile(regex)
    return [os.path.join(dp, f) \
            for dp, dn, filenames in \
            os.walk(path) \
            for f in filenames \
            if r.match(os.path.join(dp, f))]


def get_tempfile(path = os.path.join(git_root(),
                                     'data','tempfiles')):
    os.makedirs(path,exist_ok = True)
    fd = tempfile.NamedTemporaryFile(dir = path, delete = False)
    return os.path.join(path,fd.name)


def get_tempdir(path = os.path.join(git_root(),
                                    'data','tempfiles')):
    os.makedirs(path,exist_ok = True)
    return tempfile.mkdtemp(dir = path)


def remove_file(fn):
    try:
        if fn:
            os.remove(fn)
    except:
        logging.error("cannot remove file: %s" % fn)
        pass


def run_command(what, cwd, ignore_exitcode = False):
    res = subprocess.run(what,
                         cwd = cwd,
                         stderr = subprocess.PIPE,
                         stdout = subprocess.PIPE)

    if ignore_exitcode:
        return

    logging.debug("""
    command = %s
    returns = %d
    stdout  = %s
    stderr  = %s
    """ % (' '.join(what), res.returncode,
           res.stdout.decode(),
           res.stderr.decode()))

    if not res.returncode:
        return

    raise RuntimeError("""
    command has non-zero exit code
    command = %s
    returns = %d
    stdout  = %s
    stderr  = %s
    """ % (' '.join(what), res.returncode,
           res.stdout.decode(),
           res.stderr.decode()))


def get_configs(fn):
    config = configparser.ConfigParser()
    config.read(fn)
    return config


def call_matching(func, kwargs):
    """Call function by passing arguments

    """
    args = inspect.getfullargspec(func).args
    args = {k:v \
            for k,v in kwargs.items() \
            if k in args}
    return func(**args)
