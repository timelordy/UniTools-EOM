# -*- coding: utf-8 -*-


def get_user_config(script_module):
    try:
        return script_module.get_config()
    except Exception:
        return None


def save_user_config(script_module):
    try:
        script_module.save_config()
        return True
    except Exception:
        return False
