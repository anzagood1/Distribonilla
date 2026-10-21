from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.item import ItemCreate, ItemUpdate, ItemResponse
from app.crud import crud_item

router = APIRouter()

@router.post("/items/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    """
    Registra un nuevo producto en el catálogo.
    """
    return crud_item.create_item(db=db, item=item)


@router.get("/items/", response_model=List[ItemResponse])
def read_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Lista los productos del catálogo con paginación.
    """
    items = crud_item.get_items(db, skip=skip, limit=limit)
    return items


@router.put("/items/{item_id}", response_model=ItemResponse)
def update_item(item_id: int, item_update: ItemUpdate, db: Session = Depends(get_db)):
    """
    Edita la información de un producto existente.
    """
    db_item = crud_item.get_item(db, item_id=item_id)
    if db_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ítem no encontrado")
    
    return crud_item.update_item(db=db, db_item=db_item, item_update=item_update)