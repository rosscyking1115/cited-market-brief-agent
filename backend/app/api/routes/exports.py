"""Export download endpoints (Phase 4)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import Brief, Watchlist
from app.exports.service import MEDIA_TYPES, export_brief

router = APIRouter(tags=["exports"])


@router.get("/briefs/{brief_id}/export/{fmt}")
def download_export(brief_id: uuid.UUID, fmt: str, db: Session = Depends(get_db)) -> Response:
    if fmt not in MEDIA_TYPES:
        raise HTTPException(
            status_code=422, detail=f"fmt must be one of {sorted(MEDIA_TYPES)}"
        )
    brief = db.get(Brief, brief_id)
    if brief is None:
        raise HTTPException(status_code=404, detail="Brief not found")
    watchlist = db.get(Watchlist, brief.watchlist_id)
    if watchlist is None:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    try:
        filename, content, media_type = export_brief(db, brief, watchlist, fmt)
    except RuntimeError as exc:  # e.g. Playwright not installed for PDF
        raise HTTPException(status_code=501, detail=str(exc)) from exc

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
