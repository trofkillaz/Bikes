# Цена за 1 день по пакетам
PACKAGE_PRICES = {
    1: 200000,    # пакет 1 день
    3: 180000,    # пакет 3 дня
    7: 160000,    # пакет 7 дней
    14: 140000,   # пакет 14 дней
}


def calculate_total(package_days: int, selected_days: int) -> int:
    price_per_day = PACKAGE_PRICES.get(package_days, 0)
    return price_per_day * selected_days