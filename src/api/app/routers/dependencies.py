from fastapi import Request

from ..neis_client import NeisClient


def get_neis_client(request: Request) -> NeisClient:
    return request.app.state.neis_client

