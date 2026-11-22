"""GRUPO5-12: regla de negocio de stock mínimo.
"""


STOCK_MINIMO_POR_DEFECTO = 0


def es_stock_bajo(stock_actual: int, stock_minimo: int | None) -> bool:
    if stock_minimo is None:
        stock_minimo = STOCK_MINIMO_POR_DEFECTO
    if stock_minimo < 0:
        raise ValueError("El stock mínimo no puede ser negativo")
    return stock_actual <= stock_minimo
