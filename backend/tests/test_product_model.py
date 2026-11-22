from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.models.item import Categoria, Item
from app.schemas.item import ItemCreate, ItemUpdate


@pytest.fixture
def categoria(db_session):
    cat = Categoria(nombre="Uniformes")
    db_session.add(cat)
    db_session.commit()
    return cat


def valid_product(**overrides):
    data = {
        "codigo": "CAM-ESC-M",
        "nombre": "Camisa escolar blanca",
        "descripcion": "Manga corta, tela oxford",
        "precio_unitario": "12.50",
        "talla": "M",
        "stock_actual": 10,
        "stock_minimo": 3,
    }
    data.update(overrides)
    return data


def save(db_session, **overrides):
    db_session.add(Item(**ItemCreate(**valid_product(**overrides)).model_dump()))
    db_session.commit()


def test_tc_prod_01_duplicate_code_is_rejected_and_valid_record_unchanged(
    db_session,
):
    save(db_session)

    duplicate = valid_product(nombre="Otra camisa", precio_unitario="99.00")
    db_session.add(Item(**ItemCreate(**duplicate).model_dump()))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    saved = db_session.query(Item).filter_by(codigo="CAM-ESC-M").one()
    assert db_session.query(Item).count() == 1
    assert saved.nombre == "Camisa escolar blanca"
    assert saved.precio_unitario == Decimal("12.50")


@pytest.mark.parametrize("field", ["nombre", "precio_unitario"])
def test_tc_prod_01_database_rejects_missing_required_field(db_session, field):
    """La tabla tiene NOT NULL: rechaza el registro aunque se salte la API."""
    save(db_session)

    data = ItemCreate(**valid_product(codigo="OTRO-01")).model_dump()
    del data[field]
    db_session.add(Item(**data))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    assert db_session.query(Item).count() == 1
    assert db_session.query(Item).one().codigo == "CAM-ESC-M"


@pytest.mark.parametrize("field", ["nombre", "precio_unitario"])
def test_tc_prod_01_schema_rejects_missing_required_field(field):
    data = valid_product()
    del data[field]
    with pytest.raises(ValidationError):
        ItemCreate(**data)


@pytest.mark.parametrize(
    "field, value",
    [("nombre", ""), ("nombre", "   "), ("codigo", ""), ("codigo", "  ")],
)
def test_tc_prod_01_schema_rejects_empty_values(field, value):
    with pytest.raises(ValidationError):
        ItemCreate(**valid_product(**{field: value}))


def test_prod_valid_product_is_accepted():
    product = ItemCreate(**valid_product(categoria_id=1))
    assert product.codigo == "CAM-ESC-M"
    assert product.precio_unitario == Decimal("12.50")
    assert product.talla == "M"
    assert product.aplica_iva is True


def test_prod_code_is_optional_and_not_sent_as_null():
    """Sin código, no se envía NULL: la BD genera 'PRD-00001', etc."""
    data = valid_product()
    del data["codigo"]
    assert "codigo" not in ItemCreate(**data).model_dump()


def test_prod_size_is_optional():
    data = valid_product()
    del data["talla"]
    assert ItemCreate(**data).talla is None


@pytest.mark.parametrize(
    "price, accepted",
    [("-0.01", False), ("0", False), ("0.01", True), ("9999999999.99", True)],
)
def test_prod_price_boundaries(price, accepted):
    if accepted:
        product = ItemCreate(**valid_product(precio_unitario=price))
        assert product.precio_unitario == Decimal(price)
    else:
        with pytest.raises(ValidationError):
            ItemCreate(**valid_product(precio_unitario=price))


@pytest.mark.parametrize("price", ["12.555", "10000000000.00"])
def test_prod_price_with_too_many_digits_is_rejected(price):
    with pytest.raises(ValidationError):
        ItemCreate(**valid_product(precio_unitario=price))


@pytest.mark.parametrize("field", ["stock_actual", "stock_minimo"])
@pytest.mark.parametrize("value, accepted", [(-1, False), (0, True), (1, True)])
def test_prod_stock_boundaries(field, value, accepted):
    if accepted:
        assert getattr(ItemCreate(**valid_product(**{field: value})), field) == value
    else:
        with pytest.raises(ValidationError):
            ItemCreate(**valid_product(**{field: value}))


@pytest.mark.parametrize("raw, expected", [(" m ", "M"), ("xl", "XL"), ("32", "32")])
def test_prod_size_is_normalized(raw, expected):
    assert ItemCreate(**valid_product(talla=raw)).talla == expected


@pytest.mark.parametrize("size", ["", "   ", "X" * 11])
def test_prod_invalid_size_is_rejected(size):
    with pytest.raises(ValidationError):
        ItemCreate(**valid_product(talla=size))


@pytest.mark.parametrize("categoria_id", [0, -1])
def test_prod_invalid_category_id_is_rejected(categoria_id):
    with pytest.raises(ValidationError):
        ItemCreate(**valid_product(categoria_id=categoria_id))


def test_prod_partial_update_only_contains_sent_fields():
    update = ItemUpdate(talla=" l ")
    assert update.model_dump(exclude_unset=True) == {"talla": "L"}


def test_prod_product_with_category_and_size_is_persisted(db_session, categoria):
    save(db_session, categoria_id=categoria.id)

    saved = db_session.query(Item).filter_by(codigo="CAM-ESC-M").one()
    assert saved.categoria.nombre == "Uniformes"
    assert saved.talla == "M"
    assert saved.precio_unitario == Decimal("12.50")
    assert saved.activo is True and saved.aplica_iva is True
    assert saved.creado_en is not None


def test_prod_nonexistent_category_is_rejected(db_session):
    db_session.add(Item(**ItemCreate(**valid_product(categoria_id=999)).model_dump()))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_prod_same_product_in_another_size_is_allowed(db_session, categoria):
    save(db_session, categoria_id=categoria.id)
    save(db_session, categoria_id=categoria.id, codigo="CAM-ESC-L", talla="L")
    assert db_session.query(Item).filter_by(nombre="Camisa escolar blanca").count() == 2


def test_prod_duplicate_category_name_is_rejected(db_session, categoria):
    db_session.add(Categoria(nombre="Uniformes"))
    with pytest.raises(IntegrityError):
        db_session.commit()


@pytest.mark.parametrize(
    "field, value",
    [
        ("stock_actual", -1),
        ("stock_minimo", -1),
        ("precio_unitario", Decimal("0")),
        ("precio_unitario", Decimal("-5")),
    ],
)
def test_prod_database_rejects_invalid_values(db_session, field, value):
    """La BD protege los datos aunque alguien se salte la validación de la API."""
    data = ItemCreate(**valid_product()).model_dump()
    data[field] = value
    db_session.add(Item(**data))
    with pytest.raises(IntegrityError):
        db_session.commit()
