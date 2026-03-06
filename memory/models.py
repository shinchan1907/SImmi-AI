from sqlalchemy import Column, Integer, String, DateTime, Text, BigInteger, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from pgvector.sqlalchemy import Vector
from datetime import datetime

Base = declarative_base()

class MemoryEntry(Base):
    __tablename__ = "memories"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(100), index=True)
    type = Column(String(50)) # conversation, fact, tool_result
    content = Column(Text)
    embedding = Column(Vector(3072)) # Gemini/Modern dimensions
    timestamp = Column(DateTime, default=datetime.utcnow)

class TaskEntry(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True)
    description = Column(String(255))
    cron = Column(String(100), nullable=True)
    run_at = Column(DateTime, nullable=True)
    command = Column(Text)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

class PatternEntry(Base):
    __tablename__ = "patterns"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    description = Column(Text)
    code_pattern = Column(Text)
    embedding = Column(Vector(3072)) # Gemini Default
    success_count = Column(Integer, default=1)
    timestamp = Column(DateTime, default=datetime.utcnow)

class MetricEntry(Base):
    __tablename__ = "metrics"
    
    id = Column(Integer, primary_key=True)
    agent_name = Column(String(50))
    event_type = Column(String(50)) # tool_call, reasoning, task_completion
    duration = Column(Integer) # in ms
    event_metadata = Column(Text) # JSON string
    timestamp = Column(DateTime, default=datetime.utcnow)

class ExperienceEntry(Base):
    __tablename__ = "experiences"
    
    id = Column(Integer, primary_key=True)
    task_description = Column(Text)
    approach = Column(Text)
    result = Column(Text)
    status = Column(String(20)) # success, failure
    embedding = Column(Vector(3072))
    timestamp = Column(DateTime, default=datetime.utcnow)

class ReflectionEntry(Base):
    __tablename__ = "reflections"
    
    id = Column(Integer, primary_key=True)
    task_id = Column(String(50))
    observations = Column(Text)
    lessons_learned = Column(Text)
    improvement_plan = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

class PromptEntry(Base):
    __tablename__ = "prompts"
    
    id = Column(Integer, primary_key=True)
    agent_name = Column(String(50))
    version = Column(Integer)
    template = Column(Text)
    is_active = Column(Boolean, default=True)
    performance_score = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow)
