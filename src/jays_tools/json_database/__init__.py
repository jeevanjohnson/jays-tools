from .file import JsonFile
from .factory import JsonDatabase
from .database import JsonDatabaseInit
from .database import JsonDatabaseOptional

# Dev Notes:
# - __all__ is used to specify which names are visble when the module is imported using `from module import *`.
#   TLDR: Everything in __all__ is what stuff outside of its folder can get when importing from this module.
#   This is used to prevent accidental namespace pollution and to make it clear which parts of the module are intended to be used by external code.
#   If the user tries to import outside of __all__, they will get type errors in their IDE, which can help prevent accidental misuse of the module.
#   Unsure if they'll get any errors other then that. 

__all__ = [ 
    "JsonFile", 
    "JsonDatabase", 
    "JsonDatabaseInit", 
    "JsonDatabaseOptional"
]