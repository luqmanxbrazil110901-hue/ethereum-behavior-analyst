from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import KnownLabel
from app.schemas import LabelCreate, LabelResponse

router = APIRouter(prefix="/api/labels", tags=["labels"])


@router.get("", response_model=List[LabelResponse])
def list_labels(db: Session = Depends(get_db)):
    labels = db.query(KnownLabel).order_by(KnownLabel.label).all()
    return [LabelResponse.model_validate(l) for l in labels]


@router.post("", response_model=LabelResponse)
def create_label(req: LabelCreate, db: Session = Depends(get_db)):
    existing = db.query(KnownLabel).filter(KnownLabel.address == req.address.lower()).first()
    if existing:
        raise HTTPException(status_code=409, detail="Label already exists for this address")

    label = KnownLabel(
        address=req.address.lower(),
        label=req.label,
        category=req.category,
        is_toxic=req.is_toxic,
        source=req.source,
    )
    db.add(label)
    db.commit()
    db.refresh(label)
    return LabelResponse.model_validate(label)


@router.delete("/{address}")
def delete_label(address: str, db: Session = Depends(get_db)):
    label = db.query(KnownLabel).filter(KnownLabel.address == address.lower()).first()
    if not label:
        raise HTTPException(status_code=404, detail="Label not found")
    db.delete(label)
    db.commit()
    return {"detail": "Deleted"}
