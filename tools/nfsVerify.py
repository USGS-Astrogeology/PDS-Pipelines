import os, sys
import argparse
from smtplib import SMTP
from io import StringIO
from email.message import EmailMessage

class Args:
    def __init__(self):
        pass

    def parse_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--path', '-p', nargs = '?', help='')
        parser.add_argument('--email','-e',help='')
        args = parser.parse_args()
        self.path = args.path
        self.email = args.email

def main():
    args = Args()
    args.parse_args()
    exists = os.path.isfile(args.path)

    if exists is True:
        return
    else:
        email.message.EmailMessage('uh oh')
        SMTP.send_message(msg, from_addr=None , to_addrs=args.path)

if __name__ == '__main__':
    main()