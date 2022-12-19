# mysql 실행시 - systemctl로 항상 실행을 하지 않았으니 service mysql start 로 시작해야함
# mysql 의 root 패스워드는 password - 잊을까봐 적어둠
# FLASK_ENV=development FLASK_APP=app.py flask run
from datetime import datetime, timedelta

from flask import Flask, request, jsonify, current_app, Response, g
from flask.json import JSONEncoder  ##
from sqlalchemy import create_engine, text  ##
from functools import wraps
from flask_cors import CORS
import bcrypt
import jwt

# 참고로 데이터베이스를 활성화 하기전에는 데이터가 램에 저장된 상태라서 - 파일을 수정후 저장하면 항상 초기화가 된다
## Default JSON encoder는 set를 JSON으로 변환할 수 없다
## 그래서 커스텀 엔코더를 작성, set을 list로 변환하여 JSON으로 변환 가능하게 해주어야함
## 그런데 파이썬 3.9, Flask2.3, 에서는 이 커스텀 엔코더가 없어도 JSON을 작동시킴 - flask 내장함수에 업그레이드가 있는듯
class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):  # 객체가 set인경우 list로 변경해서 리턴
            return list(obj)
        return JSONEncoder.default(self, obj)

"""
app = Flask(__name__)
app.users = {}
app.id_count = 1
app.tweets = []
app.json_encoder = CustomJSONEncoder
이걸 살려두니 못찾는 404에러 뜸
"""
def get_user(user_id):
    user = current_app.database.execute(text("""
    SELECT
    id,
    name,
    email,
    profile
    FROM users
    WHERE id = :user_id
    """),{
        "user_id" : user_id
    }).fetchone()

    return {
        "id" : user["id"],
        "name" : user["name"],
        "email" : user["email"],
        "profile" : user["profile"]
    } if user else None

def insert_user(user):
    return current_app.database.execute(text("""
    INSERT INTO users(
    name,
    email,
    profile,
    hashed_password
    ) VALUES (
    :name,
    :email,
    :profile,
    :password
    )
    """), user).lastrowid

def insert_tweet(user_tweet):
    return current_app.database.execute(text("""
    INSERT INTO tweets(
    user_id,
    tweet) VALUES (
    :id,
    :tweet)
    """), user_tweet).rowcount

def insert_follow(user_follow):
    return current_app.database.execute(text("""
    INSERT INTO users_follow_list(
    user_id,
    follow_user_id) VALUES (
    :id,
    :follow)
    """), user_follow).rowcount

def insert_unfollow(user_unfollow):
    return current_app.database.execute(text("""
    DELETE FROM users_follow_list(
    WHERE user_id = :id
    AND follow_user_id = :unfollow
    """), user_unfollow).rowcount

def get_timeline(user_id):
    timeline = current_app.database.execute(text("""
    SELECT
    t.user_id,
    t.tweet
    FROM tweet t
    LEFT JOIN users_follow_list ufl ON ufl.user_id = :user_id
    WHERE t.user_id = :user_id
    OR t.user_id = ufl.follow_user_id
    """), {
        "user_id" : user_id
    }).fetchall()

    return [{
        "user_id" : tweet["user_id"],
        "tweet" : tweet["tweet"]
    } for tweet in timeline ]

def get_user_id_and_password(email):
    row = current_app.database.execute(text("""
    SELECT
    id,
    hashed_password
    FROM users
    WHERE email = :email
    """), {"email" : email}).fetchone()
    return {
        "id" : row["id"],
        "hashed_password" : row["hashed_password"]
    } if row else None

##### DECORATORS
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        access_token = request.headers.get('Authorization')
        if access_token is not None:
            try:
                payload = jwt.decodoe(access_token, current_app.config["JWT_SECRET_KEY"], "HS256")
            except jwt.InvalidTokenError:
                payload = None

            if payload is None:
                return "login_required payload None", Response(status=401)

            user_id = payload["user_id"]
            g.user_id = user_id
            g.user = get_user(user_id) if user_id else None
        else:
            return "login_required access_token is None", Response(status=401)

        return f(*args, **kwargs)
    return decorated_function


def create_app(test_config = None):
    app = Flask(__name__)

    CORS(app)

    app.json_encoder = CustomJSONEncoder

    if test_config is None:
        app.config.from_pyfile("config.py")

    else:
        app.config.update(test_config)

    database = create_engine(app.config['DB_URL'], encoding='utf-8', max_overflow=0)
    app.database = database

    @app.route("/ping", methods=["GET"])  # ping pone 테스트
    def ping():
        return "pong"

    @app.route("/sign-up", methods=["POST"])  # 회원가입 # mysql과 연결 # bcrypt 인증 구현
    def sign_up():
        new_user = request.json
        new_user["password"] = bcrypt.hashpw(
            new_user["password"].encode("UTF-8"),
            bcrypt.gensalt()
        )
        new_user_id = insert_user(new_user)
        new_user = get_user(new_user_id)

        return jsonify(new_user)

    @app.route("/login", methods=["POST"])
    def login():
        credendtial = request.json
        email = credendtial["email"]
        password = credendtial["password"]
        user_credential = get_user_id_and_password(email)

        if user_credential and bcrypt.checkpw(password.encode("UTF-8"), user_credential["hashed_password"].encode("UTF-8")):
            user_id = user_credential["id"]
            payload = {
                "user_id" : user_id,
                "exp" : datetime.utcnow() + timedelta(seconds= 60 * 60 * 24)
            }
            token = jwt.encode(payload, app.config["JWT_SECRET_KEY"], "HS256")

            return jsonify({
                "access_token" : token.encode().decode("UTF-8")   # UTF-8인 str에서 decode는 필요없다, 그래서 encode().decode()를 함
            })

        else:
            return "login user_credential error", 401


    @app.route("/tweet", methods=["POST"])  #tweet 하기
    @login_required
    def tweet():
        user_tweet = request.json
        user_tweet["id"] = g.user_id
        tweet = user_tweet["tweet"]

        if len(tweet) > 300:
            return "300자를 초과했습니다", 400

        insert_tweet(user_tweet)

        return "", 200

    """
    @app.route("/follow", methods=["POST"])  # follow 하기 
    def follow():
        payload = request.json
        user_id = int(payload["id"])
        user_id_to_follow = int(payload["follow"])
    
        if user_id not in app.users or user_id_to_follow not in app.users:
            return "사용자가 존재하지 않습니다_follow", 400
    
        user = app.users[user_id]
        user.setdefault("follow", set()).add(user_id_to_follow) # list가 아니라 set으로 하는것이 편리함
    
        return jsonify(user)
    """
    @app.route("/follow", methods=["POST"])  # follow 하기
    @login_required
    def follow():
        payload = request.json
        payload["id"] = g.user_id
        insert_follow(payload)

        return "", 200

    """
    @app.route("/unfollow", methods=["POST"])  # unfollow 하기
    def unfollow():
        payload = request.json
        user_id = int(payload["id"])
        user_id_to_follow = int(payload["unfollow"])
    
        if user_id not in app.users or user_id_to_follow not in app.users:
            return "사용자가 존재하지 않습니다 _ unfollow", 400
    
        user = app.user[user_id]
        user.setdefault("follow", set()).discard(user_id_to_follow)  # discard 특징 - 삭제하는 값이 없으면 무시하고, 삭제하는 값이 있으면 삭제
    
        return jsonify(user)
    """
    @app.route("/unfollow", methods=["POST"])  # unfollow 하기
    @login_required
    def unfollow():
        payload = request.json
        payload["id"] = g.user_id
        insert_unfollow(payload)

        return "", 200

    """
    @app.route("/timeline/<int:user_id>", methods=["GET"])  # timeline 확인
    def timeline(user_id):
        if user_id not in app.users:
            return "사용자가 존재 하지 않습니다_timeline", 400
    
        follow_list = app.users[user_id].get("follow", set())  # 팔로우하는 사용자들 리스트를 읽어 들인다.
        follow_list.add(user_id)
        timeline = [tweet for tweet in app.tweets if tweet["user_id"] in follow_list]
    
        return jsonify({
            "user_id" : user_id,
            "timeline" : timeline
        })
    """
    @app.route("/timeline/<int:user_id>", methods=["GET"])  # timeline 확인
    def timeline(user_id):
        return jsonify({
            "user_id" : user_id,
            "timeline" : get_timeline(user_id)
        })

    @app.route("/timeline", methods=["GET"])
    @login_required
    def user_timeline():
        user_id = g.user_id

        return jsonify(({
            "user_id" : user_id,
            "timeline" : get_timeline(user_id)
        }))

    return app
