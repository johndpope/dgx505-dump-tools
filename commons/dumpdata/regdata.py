import collections

from ..util import lazy_property, CachedSequence
from ..exceptions import MalformedDataError
from .messages import DumpSection
from .regvalues import (DATA_NAMES, DATA_SLICE_DICT, DATA_STRUCT_DICT,
                        DATA_MAP_DICT, DISPLAY_ORDER)


class RegDumpSection(DumpSection):
    """
    The reg section of the dump
    """
    SECTION_BYTE = 0x09
    SECTION_NAME = "Registration data"
    EXPECTED_COUNT = 2
    EXPECTED_RUN = 816

    @lazy_property
    def settings(self):
        return RegData(self.data)

    def _cereal(self):
        return self.settings._cereal()


# you can't stop me
class RegData(object):
    """
    Container for the useful data in a reg section
    """

    START_SLICE = slice(0x000, 0x004)
    SETTINGS_SLICE = slice(0x004, 0x2C4)
    END_SLICE = slice(0x2C4, 0x2C8)

    EXPECTED_SIZE = 0x2C8
    SETTING_SIZE = 0x2C

    BOOKEND = b'PSR\x03'

    def _message_format_checks(self):
        if len(self.data) != self.EXPECTED_SIZE:
            raise MalformedDataError("Data wrong length!")
        if not (self.data[self.START_SLICE]
                == self.data[self.END_SLICE] == self.BOOKEND):
            raise MalformedDataError("Invalid format")

    def __init__(self, data):

        self.data = data
        self._message_format_checks()

        # more absolute silliness for no real gain

        def make_bank(idx, s=self.SETTING_SIZE, d=data[self.SETTINGS_SLICE]):
            return RegBank(idx+1, (d[idx*s:(idx+1)*s], d[(idx+8)*s:(idx+9)*s]))

        self._settings = CachedSequence(8, make_bank)

    def get_setting(self, bank, button):
        """Get the RegSetting object corresponding to the bank and button"""
        # data is stored by button, then banks
        # (i.e. all the settings for a button are together)
        # but it's more convenient to get and display as bank, then button
        if not 1 <= button <= 2:
            raise ValueError("Invalid button: {}".format(button))
        if not 1 <= bank <= 8:
            raise ValueError("Invalid bank: {}".format(button))
        return self._settings[bank-1][button-1]

    def __iter__(self):
        """Iterate through settings, grouped by bank then button"""
        for bank in self._settings:
            yield from bank

    def _cereal(self):
        return [setting._cereal() for setting in self]


class RegBank(CachedSequence):
    __slots__ = ('bank')

    def __init__(self, bank, setting_data):
        self.bank = bank

        def make_setting(idx, bank=bank, setting_data=setting_data):
            return RegSetting(bank, idx+1, setting_data[idx])

        CachedSequence.__init__(self, len(setting_data), make_setting)


SettingValue = collections.namedtuple("SettingValue",
                                      "prop value vstr bytes unusual")


class RegSetting(object):

    def __init__(self, bank, button, data):

        self.bank = bank
        self.button = button

        self.data = data

        self._dict = dict.fromkeys(DATA_NAMES)
        self._unusual = []

        self._parse_values()

        # parse values
    def _parse_values(self):
        for key in DATA_NAMES:
            # get the data as byte slice:
            raw_bytes = self.data[DATA_SLICE_DICT[key]]
            # then unpack it:
            (raw_value,) = DATA_STRUCT_DICT[key].unpack(raw_bytes)
            # then interpret it:
            key_mapping = DATA_MAP_DICT[key]
            try:
                value, vstr = key_mapping[raw_value]
                unusual = False
            except KeyError:
                value = raw_bytes
                vstr = '<unknown {}>'.format(raw_bytes.hex())
                unusual = True
            # we build the tuple...
            val = SettingValue(key, value, vstr, raw_bytes, unusual)
            # then save it
            self._dict[key] = val
            if unusual:
                self._note_unusual(val)

    def _note_unusual(self, value):
        self._unusual.append(value)

    def __getitem__(self, key):
        return self._dict[key]

    def print_settings(self):
        print("Bank {}, Button {}:".format(self.bank, self.button))
        for key, sval in self.iter_display_order_items():
            print(" {:>18}: {:>3}".format(key, sval.vstr))

    def print_unusual(self):
        print(" {} unusual values:".format(len(self._unusual)))
        for sval in self._unusual:
            print(" {:>18}: {:>3}".format(sval.prop, sval.vstr))

    def iter_display_order_items(self):
        for key in DISPLAY_ORDER:
            yield (key, self._dict[key])

    def unusual_len(self):
        return len(self._unusual)

    def unusual_iter(self):
        return iter(self._unusual)

    def __iter__(self):
        return iter(DATA_NAMES)

    def __len__(self):
        return len(DATA_NAMES)

    def __contains__(self, item):
        return item in DATA_NAMES

    # cereal
    def _cereal(self):
        return collections.OrderedDict(
            (key, sval.vstr) for key, sval in self.iter_display_order_items())
