# -*- coding: utf-8 -*-

from sqlalchemy.types import TypeDecorator, VARCHAR
from sqlalchemy.ext import mutable
import json

class JSONEncodedDict(TypeDecorator):
    """Represents an immutable structure as a json-encoded string.

    Usage::

        JSONEncodedDict(255)

    """

    impl = VARCHAR

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value

# Make the class as a mutable dict in order to be able to do updates into the dictionnary
# and make this updates persistent into the database on a commit with SQLALchemy
mutable.MutableDict.associate_with(JSONEncodedDict)
