import os, sys
import argparse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def setup_smtp():
    server = smtplib.SMTP()
    server.connect()
    server.ehlo()
    return server

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
    server = smtplib.SMTP()
    server.connect()
    server.ehlo()
    return server
    args = Args()
    args.parse_args()
    
    exists = os.path.isfile(args.path)

    if exists is True:
        return
    else:
        body = ("missing nfs mount")
        msg = MIMEMultipart()
        msg['From'] = 'astroweb@usgs.gov'
        msg['To'] = args.email
        msg['Subject'] = 'Missing NFS Mount'
        msg.attach(MIMEText(body, 'plain'))
        text = msg.as_string()
        server.sendmail('astroweb@usgs.gov', args.email, text)
        # Update the database to reflect that the user was notified
        session.commit()
if __name__ == '__main__':
    main()




