from twp import fields

class Message(fields._Complex, metaclass=fields._ComplexType):
    def __init__(self, *args, **kwargs):
        self.extensions = kwargs.pop("extensions", [])
        super(Message, self).__init__(*args, **kwargs)

    def update_values(self, *args, **kwargs):       
        if len(args) > len(self._fields):
            raise ValueError("Too many positional args")
        for name, value in zip(self._fields.keys(), args):
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

    def __getattr__(self, name):
        if name in self._fields:
            return self._fields[name].value
        raise AttributeError("Message has no attribute named %s" % name)

    def __setattr__(self, name, value):
        try:
            self._fields[name].value = value
        except KeyError:
            super(Message, self).__setattr__(name, value)


#FIXME
class Extension(Message):
    def __init__(self, id, values, raw=None):
        self.registered_id = id
        self.values = values
        # Used for forwarding unknown extensions
        self.raw = raw

    def __repr__(self):
        return "Extension %d: %s" % (self.registered_id, self.values)

class RegisteredExtension(Extension):
    pass
