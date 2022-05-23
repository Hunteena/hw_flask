import os
import uuid
from hashlib import md5

import flask
from flask.views import MethodView

import sqlalchemy as sq
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.exc import IntegrityError

import pydantic

# PG_DSN = 'postgresql://admin:1234@localhost:5432/lesson'
PG_DSN = os.getenv('PG_DSN')

app = flask.Flask('app')
Base = declarative_base()
engine = sq.create_engine(PG_DSN)
Session = sessionmaker(bind=engine)


class UserModel(Base):
    __tablename__ = 'users'
    id = sq.Column(sq.Integer, primary_key=True)
    email = sq.Column(sq.String(50), nullable=False, unique=True)
    password = sq.Column(sq.String(100), nullable=False)
    advs = relationship('AdvModel', back_populates='owner')

    @classmethod
    def register(cls, session: Session, email: str, password: str):
        new_user = UserModel(
            email=email,
            password=str(md5(password.encode()).hexdigest())
        )
        session.add(new_user)
        try:
            session.commit()
            return new_user
        except IntegrityError:
            session.rollback()

    def check_password(self, password: str):
        return md5(password.encode()).hexdigest() == self.password

    def to_dict(self):
        return {'id': self.id,
                'email': self.email,
                'password hash': self.password}


class Token(Base):
    __tablename__ = 'tokens'
    id = sq.Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True)
    creation_time = sq.Column(sq.DateTime, server_default=sq.func.now())
    user_id = sq.Column(sq.Integer, sq.ForeignKey("users.id"))
    user = relationship(UserModel, lazy="joined")


class AdvModel(Base):
    __tablename__ = 'advs'
    id = sq.Column(sq.Integer, primary_key=True)
    title = sq.Column(sq.String(100), nullable=False)
    description = sq.Column(sq.String(500), nullable=False)
    creation_date = sq.Column(sq.Date(), server_default=sq.func.current_date())
    owner_id = sq.Column(sq.Integer, sq.ForeignKey('users.id'))
    owner = relationship(UserModel, lazy="joined", back_populates='advs')

    def to_dict(self):
        return {'id': self.id,
                'title': self.title,
                'description': self.description,
                'creation_date': self.creation_date,
                'owner_id': self.owner_id}


Base.metadata.create_all(engine)


def check_token(session):
    token = (
        session.query(Token).join(UserModel)
            .filter(
            UserModel.email == flask.request.headers.get('email'),
            Token.id == flask.request.headers.get('token')
        )
            .first()
    )
    if token is None:
        raise HTTPError(401, 'invalid token')
    return token


class AdvView(MethodView):
    def get(self, adv_id):
        with Session() as session:
            advs = session.query(AdvModel).all()
            if adv_id is None:
                return flask.jsonify([adv.to_dict() for adv in advs])
            adv = advs.filter(AdvModel.id == adv_id).first()
        if adv is None:
            raise HTTPError(404, f'no adv with id {adv_id}')
        return flask.jsonify(adv.to_dict())

    def post(self):
        with Session() as session:
            token = check_token(session)
            if not token:
                raise HTTPError(403, 'auth error')
            new_adv_data = flask.request.json
            not_nullable = ['title', 'description']
            for par in not_nullable:
                if par not in new_adv_data:
                    raise HTTPError(400, f'{par} is needed')
            new_adv = AdvModel(
                title=new_adv_data['title'],
                description=new_adv_data['description'],
                owner_id=token.user_id
            )
            session.add(new_adv)
            session.commit()
            response = flask.jsonify(new_adv.to_dict())
            response.status_code = 201
            return response

    def delete(self, adv_id):
        with Session() as session:
            adv = session.query(AdvModel).filter(AdvModel.id == adv_id).first()
            if adv is None:
                raise HTTPError(404, f'no adv with id {adv_id}')
            if adv.owner.email != flask.request.headers.get('email'):
                raise HTTPError(401, 'auth err')
            session.delete(adv)
            session.commit()
            return flask.jsonify({'message': f'adv {adv_id} deleted'})

    def patch(self, adv_id):
        with Session() as session:
            query = session.query(AdvModel).filter(AdvModel.id == adv_id)
            adv = query.first()
            if adv is None:
                raise HTTPError(404, f'no adv with id {adv_id}')
            if adv.owner.email != flask.request.headers.get('email'):
                raise HTTPError(401, 'auth err')
            query.update(flask.request.json)
            session.commit()
            return flask.jsonify(adv.to_dict())


class CreateUserValidator(pydantic.BaseModel):
    email: str
    password: str

    @pydantic.validator('email')
    def valid_email(cls, value):
        if '@' not in value:
            raise ValueError('email is not valid')
        name, domain = str(value).rsplit('@')
        if len(name) == 0 or len(domain) < 3 or '.' not in domain:
            raise ValueError('email is not valid')
        return value

    @pydantic.validator('email')
    def new_email(cls, value):
        with Session() as session:
            user = (
                session.query(UserModel)
                    .filter(UserModel.email == value)
                    .first()
            )
            if user is not None :
                raise HTTPError(401, f'user with email {value} already exists')
        return value

    @pydantic.validator('password')
    def strong_password(cls, value):
        if len(value) < 8:
            raise ValueError('password too easy')
        return value


class UserView(MethodView):
    def get(self, user_id: int):
        with Session() as session:
            token = check_token(session)
            if token.user.id != user_id:
                raise HTTPError(403, 'auth error')
            return flask.jsonify((token.user.to_dict()))

    def post(self):
        new_user_data = flask.request.json

        not_nullable = ['email', 'password']
        for par in not_nullable:
            if par not in new_user_data:
                raise HTTPError(400, f'{par} is needed')

        try:
            validated_data = CreateUserValidator(**flask.request.json).dict()
        except pydantic.ValidationError as er:
            raise HTTPError(400, er.errors())

        with Session() as session:
            new_user = UserModel.register(session, **validated_data)
            response = flask.jsonify(new_user.to_dict())
            response.status_code = 201
            return response


@app.route("/login/", methods=['POST'])
def login():
    login_data = flask.request.json
    with Session() as session:
        user = (
            session.query(UserModel)
                .filter(UserModel.email == login_data['email'])
                .first()
        )
        if user is None or not user.check_password(login_data['password']):
            raise HTTPError(401, 'incorrect user or password')
        token = Token(user_id=user.id)
        session.add(token)
        session.commit()
        return flask.jsonify({'token': token.id})


class HTTPError(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message


@app.errorhandler(HTTPError)
def handle_http_error(error):
    response = flask.jsonify({'message': error.message})
    response.status_code = error.status_code
    return response


app.add_url_rule(
    "/user/", view_func=UserView.as_view("register_user"), methods=["POST"]
)

app.add_url_rule(
    '/', view_func=AdvView.as_view('get_all_adv'), methods=['GET'],
    defaults={'adv_id': None}
)
app.add_url_rule(
    '/<int:adv_id>/', view_func=AdvView.as_view('get_adv'), methods=['GET']
)
app.add_url_rule(
    '/', view_func=AdvView.as_view('create_adv'), methods=['POST']
)
app.add_url_rule(
    '/<int:adv_id>/', view_func=AdvView.as_view('delete_adv'),
    methods=['DELETE']
)
app.add_url_rule(
    '/<int:adv_id>/', view_func=AdvView.as_view('update_adv'),
    methods=['PATCH']
)
# app.run()
