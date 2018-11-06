#!/usr/bin/env python

from pds_pipelines.RedisLock import RedisLock
from pds_pipelines.config import lock_obj
import argparse


class Args:
    def __init__(self):
        pass

    def parse_args(self):
        parser = argparse.ArgumentParser(description="Process / Queue locking tool")
        parser.add_argument('action', choices=['lock', 'unlock', 'stop'], type=str.lower, help="The action to be performed on the queue", nargs='?')
        parser.add_argument('queue', help="The queue to be locked/unlocked/stopped.", nargs='?')
        parser.add_argument('--status', help="Display the status of all queues", action='store_true')

        args=parser.parse_args()
        self.action = args.action
        self.target = args.queue
        self.status = args.status


def print_status(lock):
    print("")
    for k, v in lock.get_all().items():
        print("{}:\t{}".format(k.decode('utf-8'), status_map[v.decode('utf-8')]))
    print("")


# Map code to human-readable status
status_map = {'0': 'locked', '1': 'unlocked', '2': 'stopped'}


def main():
    redis_lock = RedisLock(lock_obj)
    args = Args()
    args.parse_args()

    if args.status:
        print_status(redis_lock)
        return

    # Inclusion of 'status' operator forces positional arguments to be optional even though they
    #  are conceptually required.  Make sure that they are specified.
    if args.action is None or args.target is None:
        print("Usage:\t ./lock_queue.py <action> <target>")
        return

    action = args.action
    target = args.target

    if target == 'all':
        action += '_all'
        target = None
    else:
        target = {'key':target}

    if target is not None:
        t = target['key']
        if redis_lock.get(t) is None:
            print("Unable to locate '{}'\nAvailble queues:".format(t))
            for key in redis_lock.get_all():
                print("\t{}".format(key))
            return
            

    func = getattr(redis_lock, action)

    # if kwargs exist pass kwargs else pass empty param set
    #  Allows for parameterization of foo(required_param) and bar().
    func(**(target or {}))

    print_status(redis_lock)

if __name__ == "__main__":
    main()
