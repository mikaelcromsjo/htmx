# lang.py
import json
import os
from typing import Dict
from functions import *
from functools import lru_cache

TRANSLATIONS: Dict[str, Dict[str, str]] = {}  # Cache

FILE_DIR = "core/lang/"

def load_translation(lang_code: str) -> Dict[str, str]:
    print(f"Loading translation for {lang_code}")  # <-- debug print
    """Load or initialize the translation dictionary for a given language code."""
    file_path = FILE_DIR + f"lang_{lang_code}.json"
    if lang_code not in TRANSLATIONS or True:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                TRANSLATIONS[lang_code] = json.load(f)
        else:
            TRANSLATIONS[lang_code] = {}
            print(f"Cant find or create language file {lang_code}")  # <-- debug print
            
    return TRANSLATIONS[lang_code]

def save_translation(lang_code: str):
    print(f"Saving translation for {lang_code}")  # <-- debug print
    """Save the current state of a language file."""
    file_path = FILE_DIR + f"lang_{lang_code}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(TRANSLATIONS[lang_code], f, indent=2, ensure_ascii=False)


def get_language():
    lang_code = "sv"
    return lang_code

def get_translator(lang_code): 
    """Return a translator function for use in templates or logic."""
    translations = load_translation(lang_code)

    def translator(text: str) -> str:
        if text in translations:
            return translations[text]
        else:
            print("fallback")
            # Add fallback and save
            translations[text] = text
            save_translation(lang_code)
            return text
    return translator

