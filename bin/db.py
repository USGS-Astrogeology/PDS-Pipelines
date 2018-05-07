from sqlalchemy import create_engine
from config import credentials as c
from sqlalchemy import MetaData, Table
from sqlalchemy.orm import mapper, sessionmaker


class Files(object):
    pass


class Archives(object):
    pass


def db_connect(cred):
    """
    Parameters
    ----------
    cred : str

    Returns
    -------
    session
    files : str
    archives : str
    engine
    """
    try:
        engine = create_engine('postgresql://{}:{}@{}:{}/{}'.format(c[cred]['user'],
                                                                    c[cred]['pass'],
                                                                    c[cred]['host'],
                                                                    c[cred]['port'],
                                                                    c[cred]['db']))
    except KeyError:
        print("Credentials not found for {}".format(cred))
    else:
        metadata = MetaData(bind=engine)
        files = None
        archives = None
        try:
            files = Table('files', metadata, autoload=True)
            archives = Table('archives', metadata, autoload=True)
            filesmapper = mapper(Files, files)
            archivesmapper = mapper(Archives, archives)
        except:
            pass
        Session = sessionmaker()
        session = Session()

        return session, files, archives, engine
