# -*- coding: utf-8 -*-

def check_keywords(text, keywords):
    text_lower = text.lower()
    matches = [k for k in keywords if k in text_lower]
    return matches