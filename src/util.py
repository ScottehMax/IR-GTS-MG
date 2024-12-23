from datetime import datetime
import json
import struct

class Util:
    @staticmethod
    def load_json(filename):
        with open(filename,"r", encoding="utf8") as f:
            return json.load(f)


class Gen4CharMap(Util):
    def __init__(self):
        self.character_map: dict = self.load_json('./data/char_map.json').get("characters", {})


    def encode_character(self, char_id):
        if char_id == 0xFFFF:
            return None
        return self.character_map.get(format(char_id, '04X'), "")


    def encode_characters(self, char_ids):
        encoded_chars = []
        for char_id in char_ids:
            encoded_char = self.encode_character(char_id)
            if encoded_char is None: break
            encoded_chars.append(encoded_char)
        return ''.join(encoded_chars)


    def decode_character(self, character):
        for id_, encoded_character in self.character_map.items():
            if character == encoded_character:
                return int(id_, 16)
        return 0xFFFF


    def decode_characters(self, characters):
        return [self.decode_character(char) for char in characters]


def timestamp_to_date(timestamp: int) -> datetime:
    year = (timestamp >> 0x30) & 0xffff
    month = (timestamp >> 0x28) & 0xff
    day = (timestamp >> 0x20) & 0xff
    hour = (timestamp >> 0x18) & 0xff
    minute = (timestamp >> 0x10) & 0xff
    second = (timestamp >> 0x08) & 0xff
    return datetime(year, month, day, hour, minute, second)


def date_to_timestamp(date: datetime) -> int:
    return (date.year & 0xffff) << 0x30 \
        | (date.month & 0xff) << 0x28 \
        | (date.day & 0xff) << 0x20 \
        | (date.hour & 0xff) << 0x18 \
        | (date.minute & 0xff) << 0x10 \
        | (date.second & 0xff) << 0x08


def encode_g5_string(s: str) -> bytes:
    """Currently only used for trainer names. Pads to 16 bytes.

    Args:
        s (str): Input string

    Returns:
        bytes: Encoded string
    """
    if len(s) > 7:
        s = s[:7]
    res = b''
    for c in s:
        res += c.encode('utf-16le')
    res += b'\xff\xff'
    if len(res) < 14:
        res += b'\x00' * (14 - len(res) % 14)
    if len(res) < 16:
        res += b'\xff\xff'
    return res


def decode_g5_string(s: bytes):
    return s.decode('utf-16le').split('\uffff')[0]
