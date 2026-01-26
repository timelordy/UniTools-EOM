PATH_NAME_TOKEN = "_CN_\u0441_\u0422\u0440\u0430\u0441\u0441\u0430 \u043a\u0430\u0431\u0435\u043b\u044c\u043d\u043e\u0439 \u043b\u0438\u043d\u0438\u0438"


def is_knk_path_name(name):
    if not name:
        return False
    return PATH_NAME_TOKEN in name
