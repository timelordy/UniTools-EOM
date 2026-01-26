# -*- coding: utf-8 -*-


def _fmt_num(value):
    try:
        if int(value) == value:
            return str(int(value))
    except Exception:
        pass
    try:
        return str(value)
    except Exception:
        return ""


def format_cable(
    mark,
    kolvo_zhil,
    kolvo_luchey,
    kolvo_provodnikov,
    kolvo_provodnikov_pe,
    sechenie,
    sechenie_pe,
    dlina,
):
    mark = mark or ""
    kolvo_zhil = int(kolvo_zhil or 0)
    kolvo_luchey = int(kolvo_luchey or 0)
    kolvo_provodnikov = int(kolvo_provodnikov or 0)
    kolvo_provodnikov_pe = int(kolvo_provodnikov_pe or 0)
    sechenie = float(sechenie or 0.0)
    sechenie_pe = float(sechenie_pe or 0.0)
    dlina = _fmt_num(dlina)

    x = u"х"
    base = ""
    if kolvo_luchey == 0:
        if kolvo_provodnikov == 0 and kolvo_provodnikov_pe == 0:
            base = f"{mark} {kolvo_zhil}{x}{_fmt_num(sechenie)}"
        elif kolvo_provodnikov != 0 and kolvo_provodnikov_pe == 0:
            base = f"{mark} {kolvo_provodnikov}({kolvo_zhil}{x}{_fmt_num(sechenie)})"
        elif kolvo_provodnikov != 0 and kolvo_provodnikov_pe != 0 and sechenie_pe == 0.0:
            base = f"{mark} {kolvo_provodnikov}({kolvo_zhil}{x}{_fmt_num(sechenie)})"
        elif kolvo_provodnikov != 0 and kolvo_provodnikov_pe != 0 and sechenie_pe != 0.0:
            base = f"{mark} {kolvo_provodnikov}({kolvo_zhil}{x}{_fmt_num(sechenie)})+{kolvo_provodnikov_pe}{x}{_fmt_num(sechenie_pe)}"
        elif kolvo_provodnikov == 0 and kolvo_provodnikov_pe != 0 and sechenie_pe != 0.0:
            base = f"{mark} {kolvo_zhil}{x}{_fmt_num(sechenie)}+{kolvo_provodnikov_pe}{x}{_fmt_num(sechenie_pe)}"
        elif kolvo_provodnikov == 0 and kolvo_provodnikov_pe != 0 and sechenie_pe == 0.0:
            base = f"{mark} {kolvo_zhil}{x}{_fmt_num(sechenie)}"
    else:
        if kolvo_provodnikov == 0 and kolvo_provodnikov_pe == 0:
            base = f"{mark} {kolvo_luchey}{x}({kolvo_zhil}{x}{_fmt_num(sechenie)})"
        elif kolvo_provodnikov != 0 and kolvo_provodnikov_pe == 0:
            base = f"{mark} {kolvo_luchey}{x}{kolvo_provodnikov}({kolvo_zhil}{x}{_fmt_num(sechenie)})"
        elif kolvo_provodnikov != 0 and kolvo_provodnikov_pe != 0 and sechenie_pe == 0.0:
            base = f"{mark} {kolvo_luchey}{x}{kolvo_provodnikov}({kolvo_zhil}{x}{_fmt_num(sechenie)})"
        elif kolvo_provodnikov != 0 and kolvo_provodnikov_pe != 0 and sechenie_pe != 0.0:
            base = f"{mark} {kolvo_luchey}{x}{kolvo_provodnikov}({kolvo_zhil}{x}{_fmt_num(sechenie)})+{kolvo_provodnikov_pe}{x}{_fmt_num(sechenie_pe)}"
        elif kolvo_provodnikov == 0 and kolvo_provodnikov_pe != 0 and sechenie_pe == 0.0:
            base = f"{mark} {kolvo_luchey}{x}({kolvo_zhil}{x}{_fmt_num(sechenie)})"
        elif kolvo_provodnikov == 0 and kolvo_provodnikov_pe != 0 and sechenie_pe != 0.0:
            base = f"{mark} {kolvo_luchey}{x}({kolvo_zhil}{x}{_fmt_num(sechenie)})+{kolvo_provodnikov_pe}{x}{_fmt_num(sechenie_pe)}"

    if not base:
        base = f"{mark} {kolvo_zhil}{x}{_fmt_num(sechenie)}"
    return f"{base}; L={dlina}"
