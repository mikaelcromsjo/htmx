# routes/tags.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db   
from core.models.models import Tag, TagLink
from fastapi import APIRouter, Form, Depends

router = APIRouter(tags=["tags"])

@router.get("/tags/search")
def search_tags(q: str = "", db: Session = Depends(get_db)):
    tags = db.query(Tag).filter(Tag.name.ilike(f"%{q}%")).limit(10).all()
    return [t.name for t in tags]

from sqlalchemy import text

@router.post("/tags/save")
def save_tags(
    tags: str = Form(...),
    object_type: str = Form(...),
    db: Session = Depends(get_db),
):
    import json
    try:
        tag_list = json.loads(tags)
    except Exception:
        tag_list = []

    # fetch existing tags for this type
    existing_tags = {t.name: t for t in db.query(Tag).filter(Tag.name.in_(tag_list)).all()}

    for name in tag_list:
        tag = existing_tags.get(name)
        if not tag:
            tag = Tag(name=name)
            db.add(tag)
            db.commit()
            db.refresh(tag)
        # insert into tag_links with only object_type

        db.execute(
            text(
                "INSERT INTO tag_links (tag_id, object_type) "
                "VALUES (:tag_id, :object_type) "
                "ON CONFLICT DO NOTHING"
            ),
            {"tag_id": tag.id, "object_type": object_type},
        )

    db.commit()

    return {"status": "ok", "tags": tag_list}


@router.get("/tags/all")
def all_tags(object_type: str, db: Session = Depends(get_db)):
    """
    Returns all tags for a given object_type (for autocomplete)
    """
    tags = (
        db.query(Tag.name)
        .join(TagLink, Tag.id == TagLink.tag_id)
        .filter(TagLink.object_type == object_type)
        .distinct()
        .all()
    )
    return [t[0] for t in tags]