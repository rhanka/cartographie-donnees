from sqlalchemy.inspection import inspect
from sqlalchemy.orm import validates
from app import db
from app.models import SearchableMixin, User, BaseModel, Organization

from app.search import remove_accent

import datetime

ownerships = db.Table(
    'ownerships',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('application_id', db.Integer, db.ForeignKey('application.id'), primary_key=True),
    db.UniqueConstraint('user_id', 'application_id')
)


class Application(SearchableMixin, BaseModel):
    __searchable__ = ['name', 'potential_experimentation', "goals", 'organization_name']

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'))
    goals = db.Column(db.Text, nullable=False)
    potential_experimentation = db.Column(db.Text)
    access_url = db.Column(db.Text)
    operator_count = db.Column(db.Integer)
    operator_count_comment = db.Column(db.String)
    user_count = db.Column(db.Integer)
    user_count_comment = db.Column(db.String)
    monthly_connection_count = db.Column(db.Integer)
    monthly_connection_count_comment = db.Column(db.String)
    context_email = db.Column(db.Text)
    owners = db.relationship('User', secondary=ownerships, lazy='subquery',
                             backref=db.backref('applications', lazy=True))
    validation_date = db.Column(db.DateTime, nullable=True)
    historic = db.Column(db.Integer, nullable=True)
    data_sources = db.relationship('DataSource', backref='application', lazy='dynamic', foreign_keys='DataSource.application_id')
    origin_data_sources = db.relationship('DataSource', backref='origin_application', lazy='dynamic', foreign_keys='DataSource.origin_application_id')

    @property
    def organization_name(self):
        return self.organization.value

    @organization_name.setter
    def organization_name(self, organization_name):
        if not organization_name:
            raise ValueError("L'organisation est un champ obligatoire.")
        organization_id = Organization.query.filter_by(value=organization_name).first()
        if not organization_id:
            raise ValueError("L'organisation '{}' n'existe pas.".format(organization_name))
        self.organization_id = organization_id.id

    @validates('access_url')
    def validate_access_url(self, key, access_url):
        if not access_url:
            return access_url
        elif "http" not in access_url:
            raise AssertionError("Veuillez saisir un url valide")
        else:
            return access_url

    @validates('context_email')
    def validate_context_email(self, key, context_email):
        if not context_email:
            return context_email

        index = context_email.find("@")
        if index == -1:
            raise AssertionError("Veuillez inclure le caractère @ dans l'addresse mail")
        elif index == 0:
            raise AssertionError("Veuillez inclure des caractères avant le @ dans l'addesse mail")
        elif index == len(context_email) - 1:
            raise AssertionError("Veuillez inclure des caractères après le @ dans l'addesse mail")
        elif " " in context_email[:index]:
            raise AssertionError("Veuillez na pas inclure le caractère \" \" avant le @ dans l'addesse mail")
        elif " " in context_email[index:]:
            raise AssertionError("Veuillez na pas inclure le caractère \" \" après le @ dans l'addesse mail")
        elif "/" in context_email[index:]:
            raise AssertionError("Veuillez na pas inclure le caractère \"/\" après le @ dans l'addesse mail")
        elif "\\" in context_email[index:]:
            raise AssertionError("Veuillez na pas inclure le caractère \"\\\" après le @ dans l'addesse mail")
        elif ";" in context_email[index:]:
            raise AssertionError("Veuillez na pas inclure le caractère \";\" après le @ dans l'addesse mail")
        elif "," in context_email[index:]:
            raise AssertionError("Veuillez na pas inclure le caractère \",\" après le @ dans l'addesse mail")
        else:
            return context_email

    def to_dict(self, populate_data_sources=False, populate_owners=True):
        result = {
            'id': self.id,
            'name': self.name,
            'potential_experimentation': self.potential_experimentation,
            'organization_name': self.organization_name,
            'goals': self.goals,
            'access_url': self.access_url,
            'operator_count': self.operator_count,
            'user_count': self.user_count,
            'monthly_connection_count': self.monthly_connection_count,
            'operator_count_comment': self.operator_count_comment,
            'user_count_comment': self.user_count_comment,
            'monthly_connection_count_comment': self.monthly_connection_count_comment,
            'context_email': self.context_email,
            'validation_date': self.validation_date.strftime("%d/%m/%Y") if self.validation_date else None,
            'historic': self.historic
        }

        if populate_data_sources:
            _list = [(data_source, remove_accent(data_source.name)) for data_source in self.data_sources]
            _list.sort(key=lambda tup: tup[1])
            data_sources = [data_source[0].to_dict() for data_source in _list]
            result['data_sources'] = data_sources
        if populate_owners:
            _list = [(user, remove_accent(user.last_name)) for user in self.owners]
            _list.sort(key=lambda tup: tup[1])
            users = [user[0].to_dict() for user in _list]
            result['owners'] = users
        return result

    def to_export(self):
        application_dict = self.to_dict(populate_owners=True)
        application_dict['owners'] = ",".join([owner['email'] for owner in application_dict['owners']])
        del application_dict["id"]
        return application_dict

    def update_from_dict(self, data):
        self.name = data.get('name')
        self.potential_experimentation = data.get('potential_experimentation')
        self.organization_id = data.get('organization_id')
        self.goals = data.get('goals')
        self.access_url = data.get('access_url')
        self.operator_count = data.get('operator_count')
        self.user_count = data.get('user_count')
        self.monthly_connection_count = data.get('monthly_connection_count')
        self.operator_count_comment = data.get("operator_count_comment")
        self.user_count_comment = data.get("user_count_comment")
        self.monthly_connection_count_comment = data.get('monthly_connection_count_comment')
        self.context_email = data.get('context_email')
        self.validation_date = data.get('validation_date')
        self.historic = data.get('historic')
        if "owners" in data:
            self.owners = [User.query.get(owner['id']) for owner in data.get('owners')]

    @staticmethod
    def from_dict(data):
        application = Application(
            id=data.get('id'),
            name=data.get('name'),
            potential_experimentation=data.get('potential_experimentation'),
            organization_id=data.get('organization_id'),
            goals=data.get('goals'),
            access_url=data.get('access_url'),
            operator_count=data.get('operator_count'),
            user_count=data.get('user_count'),
            operator_count_comment=data.get('operator_count_comment'),
            user_count_comment=data.get('user_count_comment'),
            monthly_connection_count=data.get('monthly_connection_count'),
            monthly_connection_count_comment=data.get('monthly_connection_count_comment'),
            context_email=data.get('context_email'),
            validation_date=data.get('validation_date'),
            historic=data.get('historic')
        )
        if data.get('owners'):
            application.owners = [User.query.get(owner['id']) for owner in data.get('owners')]
        return application

    @classmethod
    def filter_import_dict(cls, import_dict):
        new_import_dict = super().filter_import_dict(import_dict)
        if import_dict['owners']:
            # Transform owners string into an array of emails
            owner_emails = import_dict['owners'].split(',')
            # Replace owners' emails by owners' ids
            owners_ids = []
            for owner_email in owner_emails:
                user = User.query.filter_by(email=owner_email).first()
                if user is None:
                    raise ValueError("L'adresse email {} ne correspond "
                                     "à aucun utilisateur".format(owner_email))
                owners_ids.append(user)
            new_import_dict['owners'] = owners_ids
        else:
            new_import_dict['owners'] = []
        return new_import_dict

    @validates('operator_count')
    def validate_operator_count(self, key, operator_count):
        if not operator_count:
            return None
        elif isinstance(operator_count, int):
            return operator_count
        else:
            try:
                return int(operator_count)
            except:
                raise ValueError("Le nombre d'opérateurs dans la base de données doit être un entier")

    @validates('user_count')
    def validate_user_count(self, key, user_count):
        if not user_count:
            return None
        elif isinstance(user_count, int):
            return user_count
        else:
            try:
                return int(user_count)
            except:
                raise ValueError("Le nombre d'utilisateurs dans la base de données doit être un entier")

    @validates('monthly_connection_count')
    def validate_monthly_connection_count(self, key, monthly_connection_count):
        if not monthly_connection_count:
            return monthly_connection_count
        elif isinstance(monthly_connection_count, int):
            return monthly_connection_count
        else:
            try:
                return int(monthly_connection_count)
            except:
                raise ValueError("Le production mensuelle dans la base de données doit être un entier")

    @validates('historic')
    def validate_historic(self, key, historic):
        print(historic)
        if not historic:
            return historic
        elif isinstance(historic, int):
            return historic
        else:
            try:
                return int(historic)
            except:
                raise ValueError("L'historique dans la base de données doit être une année")

    @validates('validation_date')
    def validate_validation_date(self, key, validation_date):
        if not validation_date:
            return validation_date
        else:
            if isinstance(validation_date, datetime.date):
                return validation_date
            else:
                raise ValueError("La date de validation doit être sous le format jj/mm/aaaa")

    @classmethod
    def delete_all(cls):
        db.session.execute("DELETE FROM ownerships")
        super().delete_all()

    def __repr__(self):
        return '<Application {}>'.format(self.name)
