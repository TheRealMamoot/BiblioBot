from enum import IntEnum, auto


class States(IntEnum):
    AGREEMENT = auto()
    CREDENTIALS = auto()
    RESERVE_TYPE = auto()
    CHOOSING_DATE = auto()
    CHOOSING_TIME = auto()
    CHOOSING_DUR = auto()
    CONFIRMING = auto()
    CANCELATION_SLOT_CHOICE = auto()
    CANCELATION_CONFIRMING = auto()
    RETRY = auto()
