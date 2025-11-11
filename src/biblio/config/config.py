from dataclasses import dataclass
from enum import IntEnum, auto


class States(IntEnum):
    AGREEMENT = auto()
    CREDENTIALS = auto()
    WELCOME_BACK = auto()
    RESERVE_TYPE = auto()
    CHOOSING_DATE = auto()
    CHOOSING_TIME = auto()
    CHOOSING_DUR = auto()
    CHOOSING_AVAILABLE = auto()
    CONFIRMING = auto()
    CANCELATION_SLOT_CHOICE = auto()
    CANCELATION_CONFIRMING = auto()
    RETRY = auto()


@dataclass
class Schedule:
    hours: dict

    @staticmethod
    def weekly():
        return Schedule(
            {
                0: (9, 22),
                1: (9, 22),
                2: (9, 22),
                3: (9, 22),
                4: (9, 22),
                5: (9, 13),
                6: (9, 13),
            }
        )

    @staticmethod
    def jobs(daylight_saving=False):
        adjustment = 1 if daylight_saving else 0  # hour
        return Schedule(
            {
                'weekday': (5 + adjustment, 20 + adjustment),
                'sat': (5 + adjustment, 11 + adjustment),
                'sun': (5 + adjustment, 11 + adjustment),
                'availability': (5 + adjustment, 18 + adjustment),
                'availability_sat': (5 + adjustment, 11 + adjustment),
            }
        )

    def get_hours(self, key):
        return self.hours.get(key, (0, 0))
