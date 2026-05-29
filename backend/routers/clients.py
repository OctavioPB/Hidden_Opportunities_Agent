from fastapi import APIRouter
from src.data_sources.crm import get_all_clients, get_demo_clients

router = APIRouter(tags=["clients"])


@router.get("/clients")
def all_clients() -> list[dict]:
    return get_all_clients()


@router.get("/clients/demo")
def demo_clients() -> list[dict]:
    return get_demo_clients()
