from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.services.k8s import get_cluster_overview, get_k8s_client

router = APIRouter()


@router.get("/overview")
def cluster_overview(db: Session = Depends(get_db)) -> dict:
    return get_cluster_overview(db)


@router.get("")
def list_clusters() -> list[dict]:
    client = get_k8s_client()
    overview = client.get_overview()
    return overview["clusters"]


@router.get("/{cluster_name}/nodes")
def list_nodes(cluster_name: str) -> list[dict]:
    client = get_k8s_client()
    return client.get_nodes()


@router.get("/{cluster_name}/pods")
def list_pods(
    cluster_name: str,
    namespace: str = Query(default=""),
) -> list[dict]:
    client = get_k8s_client()
    return client.get_pods(namespace=namespace)
