# AWS RDS의 주소에 맞게 세팅
db = {
    "user" : "root",
    "password" : "password",
    "host" : "localhost",
    "port" : 3306,
    "database" : "miniter"
}

#DB_URL에 띄어쓰기 주의
DB_URL = f"mysql+mysqlconnector://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['database']}?charset=utf8"
JWT_SECRET_KEY = 'SOME_SUPER_SECRET_KEY'
JWT_EXP_DELTA_SECONDS = 7 * 24 * 60 * 60

test_db = {
    "user" : "root",
    "password" : "password",
    "host" : "localhost",
    "port" : 3306,
    "database" : "test_db"
}

test_config = {
    "DB_URL" : f"mysql+mysqlconnector://{test_db['user']}:{test_db['password']}@{test_db['host']}:{test_db['port']}/{test_db['database']}?charset=utf8",
    'JWT_SECRET_KEY' : 'SOME_SUPER_SECRET_KEY',
    'JWT_EXP_DELTA_SECONDS' : 7 * 24 * 60 * 60
}