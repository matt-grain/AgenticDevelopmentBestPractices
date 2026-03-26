from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.exceptions import InvalidTransitionError, OrderNotFoundError
from app.repositories.order_repo import OrderRepository
from app.schemas.order import OrderCreate, OrderOut, OrderStatsOut, OrderStatusUpdate
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


def get_db() -> Session:
    # placeholder — replace with real session factory
    ...


DbSession = Annotated[Session, Depends(get_db)]


def get_order_repo(db: DbSession) -> OrderRepository:
    return OrderRepository(db)


OrderRepoDep = Annotated[OrderRepository, Depends(get_order_repo)]


def get_order_service(repo: OrderRepoDep) -> OrderService:
    return OrderService(repo)


OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]


@router.get("/stats", response_model=OrderStatsOut, status_code=200)
def order_stats(service: OrderServiceDep) -> OrderStatsOut:
    return service.get_order_stats()


@router.get("/", response_model=list[OrderOut], status_code=200)
def list_orders(service: OrderServiceDep) -> list[OrderOut]:
    return service.get_orders()


@router.get("/{order_id}", response_model=OrderOut, status_code=200)
def read_order(order_id: int, service: OrderServiceDep) -> OrderOut:
    try:
        return service.get_order(order_id)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/", response_model=OrderOut, status_code=201)
def create_new_order(order: OrderCreate, service: OrderServiceDep) -> OrderOut:
    return service.create_order(order)


@router.put("/{order_id}/status", response_model=OrderOut, status_code=200)
def change_status(
    order_id: int, payload: OrderStatusUpdate, service: OrderServiceDep
) -> OrderOut:
    try:
        return service.update_order_status(order_id, payload.status)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
