
# flask pytest with built-in fixtures documentation
# https://pytest-flask.readthedocs.org/en/latest/features.html#fixtures
# flask test_client
# http://flask.pocoo.org/docs/0.10/api/#flask.Flask.test_client

import pytest
import os, json, sys, subprocess, logging
from pymongo import IndexModel
from pymongo.errors import (DuplicateKeyError, ServerSelectionTimeoutError)
from pymongo import (ASCENDING, DESCENDING)

# update sys path for importing test classes for app registration
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

# testing environmental variables
os.environ["SIMULATION_MODE"] = "1"
os.environ["LOGIN_ENABLED"] = "0"

#os.environ["MONGO_URI"] = "mongodb://localhost:27017/testdb?connectTimeoutMS=3000&socketTimeoutMS=60000&serverSelectionTimeoutMS=5000"
os.environ["MONGO_HOST"] = "localhost"
os.environ["MONGO_PORT"] = "27017"
os.environ["MONGO_DBNAME"] = "testdb"

tdir = "tests/testdata/"
db_name = "testdb"
db_version = 3

# hack to determine if running mongo version 2 or 3
try:
    cmd = "mongo --version | egrep -o \"[0-9\.]+\" | egrep \"^2\" | wc -l"
    o = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
    if o.strip() == "1": db_version = 2
except subprocess.CalledProcessError as e:
    print "failed to determine mongo version: %s" % e

# setup logging
def test_logging(logger):
    logger.setLevel(logging.DEBUG)
    logger_handler = logging.StreamHandler(sys.stdout)
    fmt ="%(process)d||%(asctime)s.%(msecs).03d||%(levelname)s||%(filename)s"
    fmt+=":(%(lineno)d)||%(message)s"
    logger_handler.setFormatter(logging.Formatter(
        fmt=fmt,
        datefmt="%Z %Y-%m-%dT%H:%M:%S")
    )
    for h in list(logger.handlers): logger.removeHandler(h)
    logger.addHandler(logger_handler)
    return logger

logger = test_logging(logging.getLogger("app"))
test_logging(logging.getLogger("tests"))

from app.models.utils import get_db
from app.models.rest import (registered_classes, Role, Universe)
from app.models.user import User

# instance relative config - config.py implies instance/config.py
from tests.api.test_rest import Rest_TestClass

# test connectivity to database before starting any tests
db = get_db()
try: db.collection_names()
except Exception as e:  sys.exit("failed to connect to database")

@pytest.fixture(scope="session")
def app(request):
    # setup test database with corresponding testdata.  Returns None on error

    print"\n" # separate logs from which test is running when printed during pytest

    # testdata to pre-load into db, indexed by db collection name containing json file with testdata
    # or directory to scan and insert into collection
    testdata = {
    }

    from app import create_app
    app = create_app("config.py")
    db = get_db()
    app.db = db
    app.client = app.test_client()

    # get all objects registred to rest API, drop db and create with proper keys
    for classname in registered_classes:
        c = registered_classes[classname]
        # drop existing collection
        logger.debug("dropping collection %s" % c._classname)
        db[c._classname].drop()
        # insert test if present 
        if c._classname in testdata: load_testdata(c._classname, testdata[c._classname])

        # create unique indexes for collection
        indexes = []
        if not c._access["expose_id"]:
            for a in c._attributes:
                if c._attributes[a].get("key", False): 
                    indexes.append((a,DESCENDING))
        if len(indexes)>0:
            logger.debug("creating indexes for %s: %s",c._classname,indexes)
            db[c._classname].create_index(indexes, unique=True)

    # if uni is enabled then required before any other object is created
    uni = Universe.load()
    uni.save()
    logger.debug("db initialized")


    # create local and admin users required to be present for all tests
    logger.debug("creating default local users")
    u1 = User(username="local", password="password", role=Role.FULL_ADMIN)
    u2 = User(username="admin", password="password", role=Role.FULL_ADMIN)
    assert (u1.save() and u2.save())

    # teardown called after all tests in session have completed
    def teardown(): pass
    request.addfinalizer(teardown)

    logger.debug("app setup completed")
    return app

def load_testdata(collection_name, testdata):
    """ load testdata into collection using mongoimport.  
        testdata is a single file or directory that needs to be scanned for .json files
    """
    # if testdata is a directory, then loop through directory
    files = []
    if os.path.isdir(testdata):
        for f in os.listdir(testdata): 
            p = "%s/%s" % (testdata, f)
            if "json" in f and not os.path.isdir(p): files.append(p) 
    elif os.path.exists(testdata): files.append(testdata)

    for f in files:
        cmd = "mongoimport --db %s --collection %s --file %s" % (db_name, collection_name, f)
        # need jsonArray only for mongo version 2
        if db_version == 2: cmd+= " --jsonArray"
        try:
            o = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            raise Exception("import exception: %s, file:%s, cmd: %s" % (e, f, cmd))

