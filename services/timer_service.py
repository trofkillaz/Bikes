import asyncio
from config import RENT_TIMEOUT_MINUTES

async def start_rent_timer(state):
    await asyncio.sleep(RENT_TIMEOUT_MINUTES * 60)
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()