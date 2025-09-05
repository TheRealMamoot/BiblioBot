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
    CONFIRMING = auto()
    CANCELATION_SLOT_CHOICE = auto()
    CANCELATION_CONFIRMING = auto()
    RETRY = auto()


@dataclass
class Schedule:
    weekly_hours: dict[int, tuple[int, int]]

    @staticmethod
    def default():
        return Schedule(
            {
                0: (9, 22),
                1: (9, 22),
                2: (9, 22),
                3: (9, 22),
                4: (9, 22),
                5: (9, 13),
                # 6: (9, 13),
            }
        )

    def get_hours(self, weekday: int) -> tuple[int, int]:
        return self.weekly_hours.get(weekday, (0, 0))
