"""
数据库模型定义
使用 SQLAlchemy ORM
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime

from .database import Base

class ExampleTable(Base):
    """
    示例表模型
    演示基本的数据模型定义
    """
    __tablename__ = "example_table"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<ExampleTable(id={self.id}, name='{self.name}')>"
    
    def to_dict(self):
        """
        将模型转换为字典
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None, 
            "active": self.active
        } 