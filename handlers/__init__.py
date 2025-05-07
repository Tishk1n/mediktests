from .user_handlers import router as user_router
from .admin_handlers import router as admin_router

router = user_router
router.include_router(admin_router)

__all__ = ["router"]
