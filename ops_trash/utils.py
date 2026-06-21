import os
import pwd
import time
import random
import string
from datetime import datetime


def now_str():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def timestamp_str():
    return datetime.now().strftime('%Y-%m-%d_%H-%M-%S')


def short_rand8():
    return ''.join(random.choice('0123456789abcdef') for _ in range(8))


def human_size(nbytes):
    if nbytes < 1024:
        return f"{nbytes}B"
    for unit in ['KB', 'MB', 'GB', 'TB']:
        nbytes /= 1024.0
        if nbytes < 1024.0:
            return f"{nbytes:.2f}{unit}"
    return f"{nbytes:.2f}PB"


def current_user():
    try:
        return pwd.getpwuid(os.getuid()).pw_name
    except Exception:
        return os.getenv('USER') or 'unknown'

