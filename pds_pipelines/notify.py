import smtplib

from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pds_pipelines.models import clusterjobs_models
from sqlalchemy import and_, or_

def setup_smtp():
    server = smtplib.SMTP()
    server.connect()
    server.ehlo()
    return server


def notify_finished(server, session):
    """ Sends an email notification when a user's product is ready for download.

    Sends an email notification to a user when their product is marked 'finished' and
    they have not received a previous notification.

    Parameters
    ----------
    server : smtplib.SMTP
        The SMTP server responsible for sending the message.
    session : sqlalchemy.session
        The sqlalchemy session by which the database will be queried.

    Returns
    -------
    None

    """
    # Get job, customer, jobtype information for entries that are marked 'finished' but the
    #  customer has not yet been notified.
    finished = session.query(clusterjobs_models.Processing,
                             clusterjobs_models.Customers,
                             clusterjobs_models.ProcessTypes).join(
                                 clusterjobs_models.Customers).join(
                                     clusterjobs_models.ProcessTypes).filter(
                                         and_(clusterjobs_models.Processing.finished != None,
                                              clusterjobs_models.Processing.notified == None,
                                              clusterjobs_models.Processing.error == None)).all()

    # For each job that fits the criteria, send a separate email
    for job, cust, proctype in finished:
        job_type = proctype.name
        job_key = job.key
        job_title = job.title
        recipient_address = cust.email

        body = ("USGS: Astrogeology Cloud Processing " + str(job_type) + " products are ready for download\n"
                "The files for this request will be removed in 14 days.\n\n"
                "\tJob Key: " + str(job_key) + "\n"
                "\tJob Title: " + str(job_title) + "\n\n"
                "For additional information regarding your request, go to\n"
                "http://astrocloud.wr.usgs.gov/index.php?view=viewjob&key=" + str(job_key) + "\n")

        msg = MIMEMultipart()
        msg['From'] = 'astroweb@usgs.gov'
        msg['To'] = recipient_address
        msg['Subject'] = 'USGS: Astrogeology Cloud Processing ' + job_type + ' - Product Notification'
        msg.attach(MIMEText(body, 'plain'))
        text = msg.as_string()
        server.sendmail('astroweb@usgs.gov', recipient_address, text)
        # Update the database to reflect that the user was notified
        job.notified = datetime.utcnow()
        session.commit()


def notify_error(server, session):
    """ Sends an email notification that a process has failed.

    Sends an email notification to a user when their product has failed and
    they have not received a previous notification.

    Parameters
    ----------
    server : smtplib.SMTP
        The SMTP server responsible for sending the message.
    session : sqlalchemy.session
        The sqlalchemy session by which the database will be queried.

    Returns
    -------
    None

    """

    finished = session.query(clusterjobs_models.Processing,
                             clusterjobs_models.Customers,
                             clusterjobs_models.ProcessTypes).join(
                                 clusterjobs_models.Customers).join(
                                     clusterjobs_models.ProcessTypes).filter(
                                         and_(clusterjobs_models.Processing.finished != None,
                                              clusterjobs_models.Processing.notified == None,
                                              clusterjobs_models.Processing.error != None)).all()

    for job, cust, proctype in finished:
        job_type = proctype.name
        job_key = job.key
        job_title = job.title
        recipient_address = cust.email
        body = ("USGS: Astrogeology Cloud Processing " + str(job_type) + " ERROR Notification\n"
                "An error occurred during your " + str(job_type) + " run -- we will look into this.\n"
                "If you have any questions, please contact:\n"
                "\tastroweb@usgs.gov\n\n"
                "\tJob Key: " + str(job_key) + "\n"
                "\tJob Title: " + str(job_title) + "\n\n"
                "For additional information regarding your request, go to\n"
                "http://astrocloud.wr.usgs.gov/index.php?view=viewjob&key=" + str(job_key) + "\n")

        msg = MIMEMultipart()
        msg['From'] = 'astroweb@usgs.gov'
        msg['To'] = recipient_address
        msg['Subject'] = 'USGS: Astrogeology Cloud Processing ' + str(job_type) + ' ERROR Notification'
        msg.attach(MIMEText(body, 'plain'))
        text = msg.as_string()
        print(text)
        server.sendmail('astroweb.usgs.gov', recipient_address, text)
        job.notified = datetime.utcnow()
        session.commit()


def notify_upcoming_purge(server, session):
    """ Sends an email notification that products will be deleted within 2 days.

    Sends an email notification to a user when their products are nearing expiration.

    Parameters
    ----------
    server : smtplib.SMTP
        The SMTP server responsible for sending the message.
    session : sqlalchemy.session
        The sqlalchemy session by which the database will be queried.

    Returns
    -------
    None
    """

    # Timestamps from 12, 13 days ago, respectively
    cutoff_low = datetime.utcnow() - timedelta(12)
    cutoff_high = cutoff_low - timedelta(1)

    # Grab items with 'notified' timestamps between 12, 13 days ago or with a 'save' timestamp between 1, 2 days in the future
    expiring = session.query(clusterjobs_models.Processing,
                             clusterjobs_models.Customers,
                             clusterjobs_models.ProcessTypes).join(
                                 clusterjobs_models.Customers).join(
                                     clusterjobs_models.ProcessTypes).filter(
                                         or_(and_(clusterjobs_models.Processing.notified <= cutoff_low,
                                                  clusterjobs_models.Processing.notified > cutoff_high,
                                                  clusterjobs_models.Processing.save == None),
                                             and_(clusterjobs_models.Processing.save > datetime.utcnow() + timedelta(1),
                                                  clusterjobs_models.Processing.save < datetime.utcnow() + timedelta(2)
                                             )
                                         )
                                     ).all()

    for job, cust, proctype in expiring:
        job_type = proctype.name
        job_key = job.key
        job_title = job.title
        recipient_address = cust.email
        body = ("USGS: Astrogeology Cloud Processing " + str(job_type) + " Product Expiration Notification\n"
                "The files for this request will be removed in 2 days.\n\n"
                "\tJob Key: " + str(job_key) + "\n"
                "\tJob Title: " + str(job_title) + "\n\n"
                "For additional information regarding your request, go to\n"
                "http://astrocloud.wr.usgs.gov/index.php?view=viewjob&key=" + str(job_key) + "\n")
        msg = MIMEMultipart()
        msg['From'] = 'astroweb@usgs.gov'
        msg['To'] = recipient_address
        msg['Subject'] = 'USGS: Astrogeology Cloud Processing ' + str(job_type) + ' Product Expiration Notification'
        msg.attach(MIMEText(body, 'plain'))
        text = msg.as_string()
        server.sendmail('astroweb.usgs.gov', recipient_address, text)
