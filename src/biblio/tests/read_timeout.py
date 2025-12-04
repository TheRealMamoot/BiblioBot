import asyncio
import logging
import time
from datetime import datetime, timedelta
from datetime import time as dtime
from unittest.mock import AsyncMock, patch

from src.biblio.config.config import Status
from src.biblio.jobs import process_reservation
from src.biblio.reservation.reservation import calculate_timeout


async def fake_set_reservation(start, end, duration, user_data, timeout):
    delay = timeout.read / 100  # Scale down for test speed
    await asyncio.sleep(delay)
    raise Exception(f"Simulated failure after {delay:.1f}s")


@patch("src.biblio.jobs.set_reservation", new_callable=AsyncMock)
@patch("src.biblio.jobs.confirm_reservation", new_callable=AsyncMock)
@patch("src.biblio.jobs.update_record", new_callable=AsyncMock)
async def test_single_record_retry_delay(
    mock_update, mock_confirm, mock_set_reservation
):
    mock_set_reservation.side_effect = fake_set_reservation

    base_record = {
        "id": "id-123",
        "status": Status.FAIL,
        "retries": 0,
        "selected_date": datetime.now().date() + timedelta(days=1),
        "start_time": dtime(hour=20, minute=30),
        "end_time": dtime(hour=21, minute=30),
        "selected_duration": 1,
        "codice_fiscale": "ABC123",
        "name": "Test User",
        "email": "test@example.com",
        "booking_code": "",
        "chat_id": None,
    }

    bot = AsyncMock()
    logging.basicConfig(level=logging.DEBUG)

    print("\n Starting timeout scaling test\n")

    retries = 0
    begining = time.perf_counter()

    for attempt in range(20):
        record = base_record.copy()
        record["retries"] = retries
        start = asyncio.get_event_loop().time()
        result = await process_reservation(record, bot)
        end = asyncio.get_event_loop().time()

        timeout = calculate_timeout(retries)
        duration = end - start
        print(
            f"Attempt {attempt} → Retry {retries} | Timeout.read = {timeout.read:.1f}s | Took ≈ {duration:.2f}s"
        )

        assert result["retries"] == retries + 1
        retries = result["retries"]

    finish = time.perf_counter()
    whole_duration = finish - begining
    print(f"Entire process took ≈ {(whole_duration * 100) / 60:.2f}m")


if __name__ == "__main__":
    asyncio.run(test_single_record_retry_delay())
