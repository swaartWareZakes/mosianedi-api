from fastapi import APIRouter, Depends
from app.dependencies import get_user_context, UserContext

router = APIRouter()

@router.get("/me")
def get_my_profile(ctx: UserContext = Depends(get_user_context)):
    return {
        "id": ctx.user_id,
        "role": ctx.role,         # "engineer" or "treasury"
        "department": ctx.department,
        "email": ctx.email
    }