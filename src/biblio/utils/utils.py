from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from dotenv import load_dotenv
from pygsheets import Worksheet


def load_env():
    project_root = Path(__file__).resolve().parents[3]
    load_dotenv(dotenv_path=project_root / '.env')


def generate_days() -> list:
    today = datetime.now(ZoneInfo('Europe/Rome')).today()
    days = []
    for i in range(7):
        next_day = today + timedelta(days=i)
        if next_day.weekday() != 6:  # Skip Sunday
            day_name = next_day.strftime('%A')
            formatted_date = next_day.strftime('%Y-%m-%d')
            days.append(f'{day_name}, {formatted_date}')
        if len(days) == 6:
            break
    return days


def update_gsheet_data_point(
    data: pd.DataFrame,
    org_data_point_id: str,
    org_data_col_name: str,
    new_value,
    worksheet: Worksheet,
) -> None:
    row_idx = data.index[data['id'] == org_data_point_id].tolist()
    sheet_row = row_idx[0] + 2  # +2 because: 1 for zero-based index, 1 for header row
    sheet_col = data.columns.get_loc(org_data_col_name) + 1  # 1-based for pygsheets
    worksheet.update_value((sheet_row, sheet_col), str(new_value))
