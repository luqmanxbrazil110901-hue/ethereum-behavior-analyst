"""Seed the database with known labels."""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal
from app.models import KnownLabel
from app.seed.known_labels import KNOWN_LABELS


def seed():
    db = SessionLocal()
    try:
        count = 0
        for item in KNOWN_LABELS:
            existing = db.query(KnownLabel).filter(KnownLabel.address == item["address"]).first()
            if not existing:
                label = KnownLabel(**item)
                db.add(label)
                count += 1

        db.commit()
        print(f"Seeded {count} new labels (total in DB: {db.query(KnownLabel).count()})")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
