"""Pure typing decisions: what counts as one key, and when to miss it."""

import random

NEIGHBORS = {
    "a": "qwsz",
    "b": "vghn",
    "c": "xdfv",
    "d": "serfcx",
    "e": "wsdr",
    "f": "drtgvc",
    "g": "ftyhbv",
    "h": "gyujnb",
    "i": "ujko",
    "j": "huikmn",
    "k": "jiolm",
    "l": "kop",
    "m": "njk",
    "n": "bhjm",
    "o": "iklp",
    "p": "ol",
    "q": "wa",
    "r": "edft",
    "s": "awedxz",
    "t": "rfgy",
    "u": "yhji",
    "v": "cfgb",
    "w": "qase",
    "x": "zsdc",
    "y": "tghu",
    "z": "asx",
    "1": "2q",
    "2": "13qw",
    "3": "24we",
    "4": "35er",
    "5": "46rt",
    "6": "57ty",
    "7": "68yu",
    "8": "79ui",
    "9": "80io",
    "0": "9op",
}

ALPHABET = "abcdefghijklmnopqrstuvwxyz"


def read_unit(source: str, index: int) -> str:
    if index < 0 or index >= len(source):
        return ""
    if index + 1 < len(source):
        pair = source[index : index + 2]
        if pair in ("\r\n", "\n\r"):
            return pair
    return source[index]


def is_newline(unit: str) -> bool:
    return unit in ("\n", "\r", "\r\n", "\n\r")


def should_mistake(rng: random.Random, per_hundred: int, unit: str) -> bool:
    if per_hundred <= 0 or len(unit) != 1 or unit.strip() == "":
        return False
    return rng.randrange(100) < max(0, min(100, per_hundred))


def sample_mistake_length(rng: random.Random, average: int) -> int:
    avg = max(1, min(20, average))
    if avg == 1:
        return 1
    roll = rng.randrange(4)
    if roll == 0:
        return avg - 1
    if roll == 3:
        return avg + 1
    return avg


def wrong_character(rng: random.Random, unit: str) -> str:
    if not unit:
        return "a"
    original = unit[0]
    lower = original.lower()
    neighbors = NEIGHBORS.get(lower, "")
    if neighbors:
        pick = neighbors[rng.randrange(len(neighbors))]
    else:
        pick = ALPHABET[rng.randrange(len(ALPHABET))]
    if pick == lower and lower.isalpha() and len(lower) == 1:
        pick = ALPHABET[(ord(lower) - 97 + 1) % 26]
    if original != lower:
        return pick.upper()
    return pick
