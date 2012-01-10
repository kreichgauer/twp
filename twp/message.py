from twp import fields

class Message(fields._Complex, metaclass=fields._ComplexType):
    def __init__(self, *values, **kwargs):
        # Only a message can have values
        self.init_values(*values, **kwargs)

    def init_values(self, *values, **kwargs):
        if len(value) > len(self._fields):
            raise ValueError("Too many positional args")
        for name, value in zip(self._fields.keys(), values):
            setattr(self, name, value)
        for name, value in kwargs.items():
            if not name in self._fields:
                raise ValueError("Unknown field name: %s" % name)
            setattr(self, name, value)

    @property
    def tag(self):
        """The Message's tag. This equals 4 plus the id. Raises a 
        ValueError if the id is larger than 7."""
        if not hasattr(self, 'id'):
            raise ValueError("Message must have an id attribute.")
        if self.id > 7:
            raise ValueError("Message id cannot be greater than 7.")
        return self.id + 4

    def __repr__(self):
        return "%s: %s" % (self.__class__, self.values)


#FIXME
class Extension(Message): pass
