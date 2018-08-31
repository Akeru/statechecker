
import logging
from .rest import (Rest, Role, api_register)

@api_register()
class Settings(Rest):

    # allow only read and update requests
    META_ACCESS = {
        "create": False,
        "delete": False,
        "bulk_update": True,    # no keys or _id requires bulk update
        "default_role": Role.FULL_ADMIN,
    }

    META = {
        "app_name": {
            "type":str, 
            "default":"AppName",
            "regex": "^(?i).{1,128}$",  # any 128 character string
            "description": "application name",
        },
        "force_https":  {
            "type": bool, 
            "default": False,
            "description": "redirect all http requests to https",
        },
        "password_reset_timeout": {
            "type": int, 
            "description": "timeout in seconds for password reset key",
            "default": 86400,       # 1 day
            "min": 60,
            "max": 31536000,        # 1 year
        },
        "password_strength_check": {
            "type":bool, 
            "default":False, 
            "description": "enable password strength check",
        },
        "session_timeout": {
            "type": int,
            "description": "maximum session length in seconds",
            "default": 86400,       # 1 day
            "min": 60,
            "max": 31536000,        # 1 year
        },
        # encrypted local user password for backend API calls
        "lpass": {
            "type":str,
            "encrypt": True,
            "read":False,
            "write":False,
            "description": "local user password set at application initialization",
        },
    }

