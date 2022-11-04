from flask import session
from wtforms.validators import DataRequired, Regexp, ValidationError
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import IntegerField, StringField, BooleanField
from urllib.request import urlopen


"""def _validate_name(form, field):
    from swag.database import item_exists
    if item_exists(field.data):
        raise ValidationError(f'"{field.data}" already exists')"""

def _validate_integer(form, field):
    try: int(field.data)
    except: raise ValidationError(f'"{field.data}" is not a valid integer')

def _validate_boolean(form, field):
    return type(field.data) == bool

def _validate_seller(form, field):
    from swag.database import is_manager
    if not is_manager(session['userinfo']['preferred_username']) and field.data not in ['CSH', session['userinfo']['preferred_username']]:
        raise ValidationError('Only managers can enter any seller')

class Item(FlaskForm):
    image = FileField('image', validators = [
        FileRequired(), FileAllowed(['jpg'])
    ])
    link = StringField('link', validators = [])
    name = StringField('name', validators = [DataRequired()])
    price = IntegerField('price', validators = [DataRequired(), _validate_integer])
    quantity = IntegerField('quantity', validators = [DataRequired(), _validate_integer])
    active = BooleanField('active', validators = [_validate_boolean])
    seller = StringField('seller', validators = [DataRequired(), _validate_seller])
    info = StringField('info', validators = [DataRequired()])

    def __init__(self, submitter = None):
        if submitter:
            super().__init__(
                link = '', 
                info = '',
                name = '',
                price=0,
                quantity=0,
                active=False,
                seller = submitter
            )
        else:
            super().__init__()

    def validate(self):
        return FlaskForm.validate(self)

class EditItem(Item):
    image = FileField('image', validators = [FileAllowed(['jpg'])])
    name = StringField('name', validators = [DataRequired()])
