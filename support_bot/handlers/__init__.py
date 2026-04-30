from .ticket_form import router as ticket_form_router
from .user import router as user_router
from .operator import router as operator_router

__all__ = ["ticket_form_router", "user_router", "operator_router"]
