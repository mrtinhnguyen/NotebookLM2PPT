from .zh_cn import TRANSLATIONS as zh_cn
from .en import TRANSLATIONS as en

SUPPORTED_LANGUAGES = {
    "zh_cn": zh_cn,
    "en": en
}

DEFAULT_LANGUAGE = "zh_cn"
_current_lang = DEFAULT_LANGUAGE

def set_language(lang):
    global _current_lang
    if lang in SUPPORTED_LANGUAGES:
        _current_lang = lang

def get_text(key, lang=None, **kwargs):
    target_lang = lang or _current_lang
    translations = SUPPORTED_LANGUAGES.get(target_lang, SUPPORTED_LANGUAGES[DEFAULT_LANGUAGE])
    text = translations.get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text
