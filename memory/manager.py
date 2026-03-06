import redis.asyncio as redis
import json
from typing import List, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from .models import Base, MemoryEntry, PatternEntry, MetricEntry, ExperienceEntry, ReflectionEntry, PromptEntry
from pgvector.sqlalchemy import Vector
import numpy as np

class MemoryManager:
    def __init__(self, db_url: str, redis_url: str):
        self.engine = create_async_engine(db_url)
        self.async_session = sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )
        self.redis = redis.from_url(redis_url, decode_responses=True)

    async def init_db(self):
        from sqlalchemy import text
        async with self.engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            await conn.run_sync(Base.metadata.create_all)

    # --- Short Term Memory (Redis) ---
    async def add_chat_history(self, user_id: int, role: str, content: str, limit: int = 10):
        key = f"chat_history:{user_id}"
        message = json.dumps({"role": role, "content": content})
        await self.redis.lpush(key, message)
        await self.redis.ltrim(key, 0, limit - 1)

    async def get_chat_history(self, user_id: int) -> List[dict]:
        key = f"chat_history:{user_id}"
        messages = await self.redis.lrange(key, 0, -1)
        return [json.loads(m) for m in reversed(messages)]

    # --- Long Term Memory (PostgreSQL + pgvector) ---
    async def store_memory(self, user_id: int, content: str, embedding: List[float], mem_type: str = "conversation"):
        async with self.async_session() as session:
            entry = MemoryEntry(
                user_id=user_id,
                content=content,
                embedding=embedding,
                type=mem_type
            )
            session.add(entry)
            await session.commit()

    async def search_memory(self, user_id: int, query_embedding: List[float], limit: int = 5):
        async with self.async_session() as session:
            stmt = select(MemoryEntry).where(MemoryEntry.user_id == user_id).order_by(
                MemoryEntry.embedding.l2_distance(query_embedding)
            ).limit(limit)
            result = await session.execute(stmt)
            return result.scalars().all()

    # --- Self-Learning Memory (Patterns) ---
    async def store_pattern(self, name: str, description: str, code: str, embedding: List[float]):
        async with self.async_session() as session:
            entry = PatternEntry(
                name=name,
                description=description,
                code_pattern=code,
                embedding=embedding
            )
            session.add(entry)
            await session.commit()

    async def search_patterns(self, query_embedding: List[float], limit: int = 3):
        async with self.async_session() as session:
            stmt = select(PatternEntry).order_by(
                PatternEntry.embedding.l2_distance(query_embedding)
            ).limit(limit)
            result = await session.execute(stmt)
            return result.scalars().all()

    # --- Observability (Metrics) ---
    async def record_metric(self, agent_name: str, event_type: str, duration_ms: int, metadata: dict = None):
        async with self.async_session() as session:
            entry = MetricEntry(
                agent_name=agent_name,
                event_type=event_type,
                duration=duration_ms,
                event_metadata=json.dumps(metadata) if metadata else "{}"
            )
            session.add(entry)
            await session.commit()

    # --- Evolution Memory (Experiences & Reflections) ---
    async def store_experience(self, task: str, approach: str, result: str, status: str, embedding: List[float]):
        async with self.async_session() as session:
            entry = ExperienceEntry(
                task_description=task,
                approach=approach,
                result=result,
                status=status,
                embedding=embedding
            )
            session.add(entry)
            await session.commit()

    async def search_experiences(self, query_embedding: List[float], limit: int = 3):
        async with self.async_session() as session:
            stmt = select(ExperienceEntry).order_by(
                ExperienceEntry.embedding.l2_distance(query_embedding)
            ).limit(limit)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def store_reflection(self, task_id: str, observations: str, lessons: str, plan: str):
        async with self.async_session() as session:
            entry = ReflectionEntry(
                task_id=task_id,
                observations=observations,
                lessons_learned=lessons,
                improvement_plan=plan
            )
            session.add(entry)
            await session.commit()
