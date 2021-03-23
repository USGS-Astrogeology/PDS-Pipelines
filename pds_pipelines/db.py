from sqlalchemy import create_engine
from pds_pipelines.config import credentials as c
from sqlalchemy.orm import sessionmaker

def db_connect(cred):
    """
    Given some credential string that is present as a key in the config
    credentials dictionary, generate the engine and associated session_maker
    objects for a database.

    Parameters
    ----------
    cred : str
           Credential string lookup from the config

    Returns
    -------
    session_maker : Object
                    sqlalchemy session maker object that can generate
                    session connections to the database
    engine : Object
             sqlalchemy engine object for the session maker
    """
    database_url = 'postgresql://{}:{}@{}:{}/{}'
    engine = create_engine(database_url.format(c[cred]['user'],
                                               c[cred]['pass'],
                                               c[cred]['host'],
                                               c[cred]['port'],
                                               c[cred]['db']), pool_pre_ping=True)

    session_maker = sessionmaker(bind=engine)
    return session_maker, engine
