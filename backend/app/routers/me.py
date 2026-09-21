from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db import get_db
from app.models import User, Workspace, WorkspaceMembership

router = APIRouter(prefix="/api", tags=["me"])


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    memberships = db.query(WorkspaceMembership).filter_by(user_id=user.id).all()
    workspaces = [db.get(Workspace, m.workspace_id) for m in memberships]
    return {
        "id": user.id,
        "discord_id": user.discord_id,
        "username": user.username,
        "avatar_url": user.avatar_url,
        "workspaces": [{"id": w.id, "name": w.name} for w in workspaces if w],
    }
