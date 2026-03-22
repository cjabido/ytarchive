"""
Tag CRUD endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
import aiosqlite

from database import get_db
from models import TagOut, TagCreate, TagUpdate

router = APIRouter()


@router.get("/tags", response_model=list[TagOut])
async def list_tags(db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute("""
        SELECT t.id, t.name, t.color, COUNT(vt.video_id) as video_count
        FROM tags t
        LEFT JOIN video_tags vt ON t.id = vt.tag_id
        GROUP BY t.id
        ORDER BY t.name
    """) as cursor:
        rows = await cursor.fetchall()
    return [TagOut(id=r["id"], name=r["name"], color=r["color"], video_count=r["video_count"]) for r in rows]


@router.post("/tags", response_model=TagOut, status_code=201)
async def create_tag(body: TagCreate, db: aiosqlite.Connection = Depends(get_db)):
    try:
        async with db.execute(
            "INSERT INTO tags (name, color) VALUES (?, ?)", [body.name, body.color]
        ) as cursor:
            tag_id = cursor.lastrowid
        await db.commit()
        return TagOut(id=tag_id, name=body.name, color=body.color, video_count=0)
    except aiosqlite.IntegrityError:
        raise HTTPException(status_code=409, detail="Tag name already exists")


@router.patch("/tags/{tag_id}", response_model=TagOut)
async def update_tag(
    tag_id: int, body: TagUpdate, db: aiosqlite.Connection = Depends(get_db)
):
    async with db.execute("SELECT * FROM tags WHERE id = ?", [tag_id]) as cursor:
        row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Tag not found")

    name = body.name if body.name is not None else row["name"]
    color = body.color if body.color is not None else row["color"]

    await db.execute(
        "UPDATE tags SET name = ?, color = ? WHERE id = ?", [name, color, tag_id]
    )
    await db.commit()

    async with db.execute(
        "SELECT COUNT(*) as cnt FROM video_tags WHERE tag_id = ?", [tag_id]
    ) as cursor:
        cnt_row = await cursor.fetchone()

    return TagOut(id=tag_id, name=name, color=color, video_count=cnt_row["cnt"])


@router.delete("/tags/{tag_id}", status_code=204)
async def delete_tag(tag_id: int, db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute("SELECT id FROM tags WHERE id = ?", [tag_id]) as cursor:
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Tag not found")
    # ON DELETE CASCADE handles video_tags cleanup
    await db.execute("DELETE FROM tags WHERE id = ?", [tag_id])
    await db.commit()
