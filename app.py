import os

import flask
from flask.views import MethodView

import sqlalchemy as sq
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# PG_DSN = 'postgresql://admin:1234@127.0.0.1:5432/lesson'
PG_DSN = os.getenv('PG_DSN')

app = flask.Flask('app')
Base = declarative_base()
engine = sq.create_engine(PG_DSN)
Session = sessionmaker(bind=engine)


class AdvModel(Base):
    __tablename__ = 'advs'
    id = sq.Column(sq.Integer, primary_key=True)
    title = sq.Column(sq.String(100), nullable=False)
    description = sq.Column(sq.String(500), nullable=False)
    creation_date = sq.Column(sq.Date(), server_default=sq.func.current_date())
    owner = sq.Column(sq.String(100), nullable=False)

    def to_dict(self):
        return {'id': self.id,
                'title': self.title,
                'description': self.description,
                'creation_date': self.creation_date,
                'owner': self.owner}


Base.metadata.create_all(engine)


class AdvView(MethodView):
    def get(self, adv_id):
        with Session() as session:
            if adv_id is None:
                advs = session.query(AdvModel).all()
                return flask.jsonify([adv.to_dict() for adv in advs])
            adv = session.query(AdvModel).filter(AdvModel.id == adv_id).first()
        if adv is None:
            raise HTTPError(404, f'no adv with id {adv_id}')
        return flask.jsonify(adv.to_dict())

    def post(self):
        new_adv_data = flask.request.json
        not_nullable = ['title', 'description', 'owner']
        for par in not_nullable:
            if par not in new_adv_data:
                raise HTTPError(400, f'{par} is needed')
        with Session() as session:
            new_adv = AdvModel(
                title=new_adv_data['title'],
                description=new_adv_data['description'],
                owner=new_adv_data['owner']
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
            session.delete(adv)
            session.commit()
            return flask.jsonify({'message': f'adv {adv_id} deleted'})


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
    '/adv/', view_func=AdvView.as_view('get_all_adv'), methods=['GET'],
    defaults={'adv_id': None}
)
app.add_url_rule(
    '/adv/<int:adv_id>/', view_func=AdvView.as_view('get_adv'), methods=['GET']
)
app.add_url_rule(
    '/adv/', view_func=AdvView.as_view('create_adv'), methods=['POST']
)
app.add_url_rule(
    '/adv/<int:adv_id>/', view_func=AdvView.as_view('delete_adv'),
    methods=['DELETE']
)
# app.run()
