from fastapi import APIRouter, Request
from pydantic import BaseModel

from pocket import __version__

router = APIRouter(tags=['health'])


class Health(BaseModel):
    status: str
    version: str
    provider: str


@router.get('/health', response_model=Health)
def health(request: Request) -> Health:
    """Liveness for a monitor: the process answers and says which model provider it runs."""
    return Health(status='ok', version=__version__, provider=request.app.state.provider.name)
