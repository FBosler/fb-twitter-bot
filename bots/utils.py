import numpy as np
import boto3
import datetime
import os
import json
import pickle
import csv
import shutil
import time
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

S3_BUCKET_NAME = 'fb-twitterbot'
DEFAULT_TMP_FOLDER = '/tmp'


def random_execute(do_nothing_prob=.5, max_delay=60):
    def decorator_random(func):
        def wrapper_random(*args, **kwargs):
            if np.random.random() < do_nothing_prob:
                logger.info(f'Doing nothing this time')
            else:
                wait = np.random.randint(max_delay)
                logger.info(f'Waiting {wait} seconds')
                time.sleep(wait)
                return func(*args, **kwargs)
        return wrapper_random
    return decorator_random


def sigmoid(x):
    return np.exp(x) / (np.exp(x) + 1)


def scaled_sigmoid(x: int, max_score: int = 20, stretch: int = 10,  center: int = 0) -> float:
    """
    function that will result values close to 0 or equal to 0 for small values and continuously go up to max_score.
    :param x: Input value
    :param stretch: parameter to control how long it roughly takes to go from 0 to max_score
    :param max_score: maximum achievable score
    :param center: center of the function, default of 0
    :return: float between 0 and max_score
    """
    stretch /= 5
    x = (x + center) / stretch
    return round(sigmoid(x) * max_score, 2)


def followed_to_following_ratio(user):
    if user.friends_count == 0:
        return 0

    if (not user.followers_count) or (user.followers_count == 0):
        return max(round(np.log(user.friends_count) * 10, 2), 0)

    try:
        return max(round(np.log(user.friends_count/(user.followers_count or 1)) * 10, 2), 0)
    except:
        return 0


def created_at_score(inp, **kwargs):
    """
    Inverse Sigmoid function to model decay from mmax_val to 0 over a given time
    """
    days_since_creation = (datetime.datetime.today() - inp.created_at.replace(tzinfo=None)).days

    kwargs['center'] = kwargs.get('center', 3)

    return round(scaled_sigmoid(-days_since_creation, **kwargs), 2)


def sync_s3_data(*args, folder='history', **kwargs):
    """
    Sync PersistentDict to disk and upload to s3.

    :param *args: (list of) file path or (list of) persistentdict
    :param folder: s3folder
    :param **kwargs:
       - folder: folder name of the remote s3 file

    For example, we now have a PersistentDict named `mapping` which is associated
    with a file on the disk `/tmp/mapping.json`.

    >>> sync_s3_data(mapping)

    will save the mapping dictionary to disk and
    overwrite the file `/tmp/mapping.json`, and upload it to s3.

    """
    # initialize bucket
    bucket = boto3.resource('s3').Bucket(S3_BUCKET_NAME)

    results = []
    for arg in args:
        if isinstance(arg, PersistentDict) and arg.filename:
            arg.sync()
            source = arg.filename
            target = os.path.join(folder, arg.filename.split('/')[-1])
            try:
                bucket.upload_file(source, target)
                results.append(
                    ('from (local): ' + source, 'to (s3): ' + target))
            except Exception as e:
                raise ConnectionError(
                    'Could not upload s3 mappings: {}'.format(e))

        elif isinstance(arg, str) and kwargs.get('folder'):
            # TODO test if filepath exists
            source = arg
            target = os.path.join(kwargs.get('folder'), arg.split('/')[-1])
            try:
                bucket.upload_file(source, target)
                results.append(
                    ('from (local): ' + source, 'to (s3): ' + target))
            except Exception as e:
                raise ConnectionError(
                    'Could not upload s3 mappings: {}'.format(e))
        else:
            raise ValueError(
                'Input is not a PersistentDict or folder is missing has a filename for argument: {}'.format(arg))
    return 'Successfully uploaded S3 Data: {}'.format(results)


def get_s3_data(*args, folder='history'):
    """
    Create a PersistentDict dictionary from a json file on the disk and
    associate this file with the dictionary. Default file path is '/tmp/'

    >>> mapping = get_s3_data('mapping.json')

    """
    bucket = boto3.resource('s3').Bucket(S3_BUCKET_NAME)
    results = []
    for arg in args:
        if isinstance(arg, str):
            source = os.path.join(folder, arg)
            target = os.path.join(DEFAULT_TMP_FOLDER, arg)
            try:
                bucket.download_file(source, target)
                local_mapping = PersistentDict(target, format='json')
                results.append(local_mapping)
            except Exception as e:
                raise ConnectionError(
                    'Could not donwload s3 mappings: {}'.format(e))
        else:
            raise ValueError(
                'Input is not a PersistentDict or has a filename for argument: {}'.format(arg))
    if len(results) == 1:
        return results[0]
    else:
        return results


class PersistentDict(dict):
    ''' Persistent dictionary with an API compatible with shelve and anydbm.

    The dict is kept in memory, so the dictionary operations run as fast as
    a regular dictionary.

    Write to disk is delayed until close or sync (similar to gdbm's fast mode).

    Input file format is automatically discovered.
    Output file format is selectable between pickle, json, and csv.
    All three serialization formats are backed by fast C implementations.
    '''

    def __init__(self, filename, flag='c', mode=None, format='pickle', *args, **kwds):
        self.flag = flag                    # r=readonly, c=create, or n=new
        self.mode = mode                    # None or an octal triple like 0644
        self.format = format                # 'csv', 'json', or 'pickle'
        self.filename = filename
        if flag != 'n' and os.access(filename, os.R_OK):
            fileobj = open(filename, 'rb' if format == 'pickle' else 'r')
            with fileobj:
                self.load(fileobj)
        dict.__init__(self, *args, **kwds)

    def sync(self):
        '''
        Write the dictionary to disk
        '''
        if self.flag == 'r':
            return
        filename = self.filename
        tempname = filename + '.tmp'
        fileobj = open(tempname, 'wb' if self.format == 'pickle' else 'w')
        try:
            self.dump(fileobj)
        except Exception:
            os.remove(tempname)
            raise
        finally:
            fileobj.close()
        shutil.move(tempname, self.filename)    # atomic commit
        if self.mode is not None:
            os.chmod(self.filename, self.mode)

    def close(self):
        '''
        Write the dictionary to the corresponding file on disk
        '''
        self.sync()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    def dump(self, fileobj):
        if self.format == 'csv':
            csv.writer(fileobj).writerows(self.items())
        elif self.format == 'json':
            json.dump(self, fileobj, indent=2, separators=(',', ':'))
        elif self.format == 'pickle':
            pickle.dump(dict(self), fileobj, 2)
        else:
            raise NotImplementedError('Unknown format: ' + repr(self.format))

    def load(self, fileobj):
        # try formats from most restrictive to least restrictive
        for loader in (pickle.load, json.load, csv.reader):
            fileobj.seek(0)
            try:
                return self.update(loader(fileobj))
            except Exception:
                pass
        raise ValueError('File not in a supported format')


if __name__ == '__main__':
    print(scaled_sigmoid(0, stretch=10))
    print(scaled_sigmoid(5, stretch=10))
    print(scaled_sigmoid(5, stretch=20))
    print(scaled_sigmoid(20, stretch=10))
    print(scaled_sigmoid(20, stretch=100))
