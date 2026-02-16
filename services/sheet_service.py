class SheetsService:

    async def create_rent(self, data: dict):
        pass

    async def close_rent(self, rent_id: int):
        pass

    async def get_open_rents(self):
        return []


sheets_service = SheetsService()

async def get_active_rents():
    return await sheets_service.get_open_rents()

async def close_rent_by_number(rent_id: int):
    return await sheets_service.close_rent(rent_id)