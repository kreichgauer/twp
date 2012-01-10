from twp import fields

class Message(fields._Complex, metaclass=fields._ComplexType):
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
        return "%s: %s" % (self.__class__, self.get_fields())


#FIXME
class Extension(Message): pass
