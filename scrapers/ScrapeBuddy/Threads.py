import threading

from typing import Callable, TypeAlias
from functools import wraps
from py_common import log

ThreadBatch: TypeAlias =  list[threading.Thread]

# def useThread(batch: ThreadBatch, target: Callable):
#     @wraps(target)
#     def initThread(*args, **kwargs):
#         t = threading.Thread(target=target, args=args, kwargs=kwargs)
#         batch.append(t)
#         t.start()
#     return initThread
def useThread(batch: ThreadBatch):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            t = threading.Thread(target=func, args=args, kwargs=kwargs)
            batch.append(t)
            t.start()
        return wrapper
    return decorator

def awaitThreads(batch: ThreadBatch, timeout: float | None = None):
    for v in batch:
        v.join(timeout)