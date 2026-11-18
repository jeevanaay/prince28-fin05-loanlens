from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from loanlens.api.deps import RepositoryDep
from loanlens.api.schemas import DocumentListResponse, Record

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    repository: RepositoryDep,
    q: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    rows = await repository.search(q)

    return {
        "total": len(rows),
        "limit": limit,
        "offset": offset,
        "items": rows[offset : offset + limit],
    }


@router.get("/{doc_id}", response_model=Record)
async def get_document(
    doc_id: str,
    repository: RepositoryDep,
) -> dict:
    record = await repository.get(doc_id)

    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"No document with id '{doc_id}'.",
        )

    return record
