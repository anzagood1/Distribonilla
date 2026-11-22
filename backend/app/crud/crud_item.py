from sqlalchemy.orm import Session
from app.models.item import Item
from app.schemas.item import ItemCreate, ItemUpdate


def get_item(db: Session, item_id: int):
    return db.query(Item).filter(Item.id == item_id).first()


def get_items(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Item).offset(skip).limit(limit).all()


def get_low_stock_items(db: Session, skip: int = 0, limit: int = 100):
    """GRUPO5-12: productos activos con stock_actual <= stock_minimo."""
    return (
        db.query(Item)
        .filter(Item.activo.is_(True), Item.stock_actual <= Item.stock_minimo)
        .order_by(Item.stock_actual - Item.stock_minimo, Item.nombre)
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_item(db: Session, item: ItemCreate):
    db_item = Item(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def update_item(db: Session, db_item: Item, item_update: ItemUpdate):
    update_data = item_update.model_dump(
        exclude_unset=True
    )  # Solo actualiza lo que el usuario envió

    for key, value in update_data.items():
        setattr(db_item, key, value)

    db.commit()
    db.refresh(db_item)
    return db_item
