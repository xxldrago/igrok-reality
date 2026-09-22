"""Groups and Specialist Quests API — CRUD + member management."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.dependencies import get_current_user, require_role
from app.shared.database import session_factory
from app.shared.models.group import Group
from app.shared.models.specialist_quest import SpecialistQuest
from app.shared.models.user import User

router = APIRouter(prefix="/api/admin", tags=["groups"])


# ── Schemas ──────────────────────────────────────────────────────────


class GroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., pattern=r"^(curator|leader|specialist|quest)$")
    owner_id: Optional[UUID] = None
    max_members: int = Field(default=10, ge=1, le=100)


class GroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    owner_id: Optional[UUID] = None
    max_members: Optional[int] = Field(None, ge=1, le=100)


class GroupResponse(BaseModel):
    id: UUID
    name: str
    type: str
    owner_id: Optional[UUID] = None
    max_members: int
    member_count: int = 0


class GroupMemberRequest(BaseModel):
    user_id: UUID


class SpecialistQuestCreate(BaseModel):
    group_id: UUID
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    day_number: int = Field(..., ge=1, le=90)
    media_file_id: Optional[str] = None
    xp_reward: int = Field(default=10, ge=0)


class SpecialistQuestUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = None
    day_number: Optional[int] = Field(None, ge=1, le=90)
    media_file_id: Optional[str] = None
    xp_reward: Optional[int] = Field(None, ge=0)


class SpecialistQuestResponse(BaseModel):
    id: UUID
    group_id: UUID
    specialist_id: UUID
    title: str
    content: str
    day_number: int
    media_file_id: Optional[str] = None
    xp_reward: int
    published_at: Optional[datetime] = None


# ── Groups CRUD ──────────────────────────────────────────────────────


async def _count_members(group_id: UUID) -> int:
    async with session_factory() as session:
        result = await session.execute(
            select(User).where(User.group_id == group_id)
        )
        return len(list(result.scalars().all()))


@router.get(
    "/groups",
    response_model=list[GroupResponse],
    dependencies=[Depends(require_role("master", "leader", "curator"))],
)
async def list_groups(
    group_type: Optional[str] = Query(None, pattern=r"^(curator|leader|specialist|quest)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> list[GroupResponse]:
    async with session_factory() as session:
        q = select(Group)
        if group_type:
            q = q.where(Group.type == group_type)
        q = q.offset((page - 1) * page_size).limit(page_size)
        result = await session.execute(q)
        groups = list(result.scalars().all())

    out = []
    for g in groups:
        mc = await _count_members(g.id)
        out.append(GroupResponse(
            id=g.id, name=g.name, type=g.type,
            owner_id=g.owner_id, max_members=g.max_members,
            member_count=mc,
        ))
    return out


@router.post(
    "/groups",
    response_model=GroupResponse,
    dependencies=[Depends(require_role("master", "leader"))],
)
async def create_group(req: GroupCreate) -> GroupResponse:
    async with session_factory() as session:
        # Validate owner exists (quest groups are ownerless)
        if req.owner_id is not None:
            owner = await session.execute(select(User).where(User.id == req.owner_id))
            if owner.scalar_one_or_none() is None:
                raise HTTPException(status_code=404, detail="Owner user not found")
        elif req.type != "quest":
            raise HTTPException(
                status_code=400, detail="Mentor groups require an owner"
            )

        group = Group(
            name=req.name,
            type=req.type,
            owner_id=req.owner_id,
            max_members=req.max_members,
        )
        session.add(group)
        await session.commit()
        await session.refresh(group)

    return GroupResponse(
        id=group.id, name=group.name, type=group.type,
        owner_id=group.owner_id, max_members=group.max_members,
        member_count=0,
    )


@router.get(
    "/groups/{group_id}",
    response_model=GroupResponse,
    dependencies=[Depends(require_role("master", "leader", "curator"))],
)
async def get_group(group_id: UUID) -> GroupResponse:
    async with session_factory() as session:
        result = await session.execute(select(Group).where(Group.id == group_id))
        group = result.scalar_one_or_none()
        if group is None:
            raise HTTPException(status_code=404, detail="Group not found")
        mc = await _count_members(group.id)
    return GroupResponse(
        id=group.id, name=group.name, type=group.type,
        owner_id=group.owner_id, max_members=group.max_members,
        member_count=mc,
    )


@router.put(
    "/groups/{group_id}",
    response_model=GroupResponse,
    dependencies=[Depends(require_role("master", "leader"))],
)
async def update_group(group_id: UUID, req: GroupUpdate) -> GroupResponse:
    async with session_factory() as session:
        result = await session.execute(select(Group).where(Group.id == group_id))
        group = result.scalar_one_or_none()
        if group is None:
            raise HTTPException(status_code=404, detail="Group not found")
        if req.name is not None:
            group.name = req.name
        if req.owner_id is not None:
            group.owner_id = req.owner_id
        if req.max_members is not None:
            group.max_members = req.max_members
        await session.commit()
        await session.refresh(group)
        mc = await _count_members(group.id)
    return GroupResponse(
        id=group.id, name=group.name, type=group.type,
        owner_id=group.owner_id, max_members=group.max_members,
        member_count=mc,
    )


@router.delete(
    "/groups/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role("master"))],
)
async def delete_group(group_id: UUID) -> None:
    async with session_factory() as session:
        result = await session.execute(select(Group).where(Group.id == group_id))
        group = result.scalar_one_or_none()
        if group is None:
            raise HTTPException(status_code=404, detail="Group not found")
        # Unlink members first
        members = await session.execute(
            select(User).where(User.group_id == group_id)
        )
        for u in members.scalars().all():
            u.group_id = None
        await session.delete(group)
        await session.commit()


# ── Group Members ────────────────────────────────────────────────────


@router.post(
    "/groups/{group_id}/members",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("master", "leader"))],
)
async def add_group_member(group_id: UUID, req: GroupMemberRequest) -> dict:
    """Add a player to a group. Checks max_members limit."""
    async with session_factory() as session:
        result = await session.execute(select(Group).where(Group.id == group_id))
        group = result.scalar_one_or_none()
        if group is None:
            raise HTTPException(status_code=404, detail="Group not found")

        user_result = await session.execute(select(User).where(User.id == req.user_id))
        user = user_result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        mc = await _count_members(group_id)
        if mc >= group.max_members:
            raise HTTPException(status_code=400, detail=f"Group is full (max {group.max_members})")

        user.group_id = group_id
        await session.commit()

    return {"user_id": str(req.user_id), "group_id": str(group_id), "status": "added"}


@router.delete(
    "/groups/{group_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role("master", "leader"))],
)
async def remove_group_member(group_id: UUID, user_id: UUID) -> None:
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        if user.group_id != group_id:
            raise HTTPException(status_code=400, detail="User is not in this group")
        user.group_id = None
        await session.commit()


# ── Specialist Quests CRUD ───────────────────────────────────────────


@router.get(
    "/specialist-quests",
    response_model=list[SpecialistQuestResponse],
    dependencies=[Depends(require_role("master", "leader", "specialist"))],
)
async def list_specialist_quests(
    group_id: Optional[UUID] = Query(None),
    day_number: Optional[int] = Query(None, ge=1, le=90),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
) -> list[SpecialistQuestResponse]:
    async with session_factory() as session:
        q = select(SpecialistQuest)
        if group_id:
            q = q.where(SpecialistQuest.group_id == group_id)
        if day_number is not None:
            q = q.where(SpecialistQuest.day_number == day_number)
        q = q.order_by(SpecialistQuest.day_number).offset((page - 1) * page_size).limit(page_size)
        result = await session.execute(q)
        return [
            SpecialistQuestResponse(
                id=q.id, group_id=q.group_id, specialist_id=q.specialist_id,
                title=q.title, content=q.content, day_number=q.day_number,
                media_file_id=q.media_file_id, xp_reward=q.xp_reward,
                published_at=q.published_at,
            )
            for q in result.scalars().all()
        ]


@router.post(
    "/specialist-quests",
    response_model=SpecialistQuestResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("master", "specialist"))],
)
async def create_specialist_quest(
    req: SpecialistQuestCreate,
    current_user: dict = Depends(get_current_user),
) -> SpecialistQuestResponse:
    # Specialists can only create quests for their own group
    caller_role = current_user.get("role", "")
    caller_username = current_user.get("username", "")

    async with session_factory() as session:
        specialist_id: UUID
        if caller_role == "specialist":
            result = await session.execute(
                select(User).where(User.username == caller_username)
            )
            caller_user = result.scalar_one_or_none()
            if caller_user is None:
                raise HTTPException(status_code=403, detail="Caller user not found")
            if caller_user.group_id is None:
                raise HTTPException(status_code=403, detail="You have no assigned group")
            group_result = await session.execute(
                select(Group).where(Group.id == req.group_id)
            )
            group = group_result.scalar_one_or_none()
            if group is None:
                raise HTTPException(status_code=404, detail="Group not found")
            if group.owner_id != caller_user.id:
                raise HTTPException(status_code=403, detail="You can only create quests for your own group")
            # Require the caller to own the group (as specialist) OR be assigned as member-owner
            specialist_id = caller_user.id
        else:
            # Master creating on behalf: use the group owner (the specialist)
            group_result = await session.execute(
                select(Group).where(Group.id == req.group_id)
            )
            group = group_result.scalar_one_or_none()
            if group is None:
                raise HTTPException(status_code=404, detail="Group not found")
            specialist_id = group.owner_id

        quest = SpecialistQuest(
            group_id=req.group_id,
            specialist_id=specialist_id,
            title=req.title,
            content=req.content,
            day_number=req.day_number,
            media_file_id=req.media_file_id,
            xp_reward=req.xp_reward,
        )
        session.add(quest)
        await session.commit()
        await session.refresh(quest)

    return SpecialistQuestResponse(
        id=quest.id, group_id=quest.group_id, specialist_id=quest.specialist_id,
        title=quest.title, content=quest.content, day_number=quest.day_number,
        media_file_id=quest.media_file_id, xp_reward=quest.xp_reward,
        published_at=quest.published_at,
    )


@router.put(
    "/specialist-quests/{quest_id}",
    response_model=SpecialistQuestResponse,
    dependencies=[Depends(require_role("master", "specialist"))],
)
async def update_specialist_quest(quest_id: UUID, req: SpecialistQuestUpdate) -> SpecialistQuestResponse:
    async with session_factory() as session:
        result = await session.execute(select(SpecialistQuest).where(SpecialistQuest.id == quest_id))
        quest = result.scalar_one_or_none()
        if quest is None:
            raise HTTPException(status_code=404, detail="Quest not found")
        if req.title is not None:
            quest.title = req.title
        if req.content is not None:
            quest.content = req.content
        if req.day_number is not None:
            quest.day_number = req.day_number
        if req.media_file_id is not None:
            quest.media_file_id = req.media_file_id
        if req.xp_reward is not None:
            quest.xp_reward = req.xp_reward
        await session.commit()
        await session.refresh(quest)
    return SpecialistQuestResponse(
        id=quest.id, group_id=quest.group_id, specialist_id=quest.specialist_id,
        title=quest.title, content=quest.content, day_number=quest.day_number,
        media_file_id=quest.media_file_id, xp_reward=quest.xp_reward,
        published_at=quest.published_at,
    )


@router.delete(
    "/specialist-quests/{quest_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role("master"))],
)
async def delete_specialist_quest(quest_id: UUID) -> None:
    async with session_factory() as session:
        result = await session.execute(select(SpecialistQuest).where(SpecialistQuest.id == quest_id))
        quest = result.scalar_one_or_none()
        if quest is None:
            raise HTTPException(status_code=404, detail="Quest not found")
        await session.delete(quest)
        await session.commit()
