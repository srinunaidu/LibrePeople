from sqlalchemy.orm import Session
from app.models.recruiting import Offer
from app.schemas.recruiting import OfferCreate, OfferUpdate


def get_offer(db: Session, offer_id: int) -> Offer | None:
    return db.query(Offer).filter(Offer.id == offer_id).first()


def get_offer_by_number(db: Session, offer_number: str) -> Offer | None:
    return db.query(Offer).filter(Offer.offer_number == offer_number).first()


def get_offers(
    db: Session, skip: int = 0, limit: int = 100, status: str | None = None
) -> list[Offer]:
    query = db.query(Offer)
    if status:
        query = query.filter(Offer.status == status)
    return query.offset(skip).limit(limit).all()


def create_offer(db: Session, offer_in: OfferCreate) -> Offer:
    db_obj = Offer(**offer_in.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_offer(db: Session, db_obj: Offer, offer_in: OfferUpdate) -> Offer:
    update_data = offer_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj
