
class CustomError(Exception):
    pass

class CustomTypeError(CustomError):
    pass

class CustomValueError(CustomError):
    pass
class AuthenticationError(CustomError):
    pass

class ImageProcessingError(CustomError):
    pass