""" This file defines some exceptions for the AOMR Toolkit. """

class AomrError(Exception):
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return repr(self.message)

class AomrFilePathNotSetError(AomrError): pass