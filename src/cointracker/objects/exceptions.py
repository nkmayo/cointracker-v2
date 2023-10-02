class AssetNotFoundError(BaseException):
    def __init__(self, message):
        # Call the base class constructor with the parameters it needs
        super().__init__(message)


class NoMatchingPoolError(BaseException):
    def __init__(self, message):
        # Call the base class constructor with the parameters it needs
        super().__init__(message)


class IncorrectPoolFormat(BaseException):
    def __init__(self, message):
        # Call the base class constructor with the parameters it needs
        super().__init__(message)
