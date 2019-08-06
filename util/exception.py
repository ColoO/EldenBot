class BotError(Exception):
    """represent all error from bot"""

class Error(BotError):
    """Basic error, for undle user"""

class CritialError(BotError):
    """THIS ... BOT ... IS ON FIIIIIIIIRE"""

class InvalidArgs(BotError):
    """represent a error when a user try a command"""

class ALEDException(BotError):
    """Error that should never occurate"""

class NotFound(BotError):
    """NotFound"""