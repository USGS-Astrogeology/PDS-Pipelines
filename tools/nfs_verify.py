import os
import argparse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import socket

class Args:
    def __init__(self):
        pass

    def parse_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--path', '-p', nargs = '?', help='file path')
        parser.add_argument('--email','-e', nargs='+',help='list of emails')
        args = parser.parse_args()
        self.path = args.path
        self.email = args.email

def main():
    server = smtplib.SMTP()
    server.connect()
    server.ehlo()
    args = Args()
    args.parse_args()

    exists = os.path.isfile(args.path)

    if exists:
        print('NFS Mount was found')
    else:
        time = datetime.now().timestamp()
        readable = datetime.fromtimestamp(time).isoformat()
        body = ('stale NFS connection to PDS SAN ' + str(readable) +
        ' ' + str(socket.gethostname()))
        msg = MIMEMultipart()
        msg['From'] = 'astroweb@usgs.gov'
        msg['To'] = ','.join(args.email)
        msg['Subject'] = ('Missing NFS Mount ' + str(socket.gethostname()))
        msg.attach(MIMEText(body, 'plain'))
        text = msg.as_string()
        server.sendmail('astroweb@usgs.gov', args.email, text)
        server.quit


if __name__ == '__main__':
    main()
