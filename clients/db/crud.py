"""
数据库 CRUD 操作
包含各种模型的增删改查操作
"""

import logging
from typing import List, Optional, Union, Dict, Any
from sqlalchemy.orm import Session

from .models import ExampleTable

logger = logging.getLogger(__name__)

# ExampleTable 的 CRUD 操作

def create_example_item(db: Session, data: Dict[str, Any]) -> ExampleTable:
    """
    创建一个新的示例项
    
    参数:
    - db: 数据库会话
    - data: 包含字段值的字典
    
    返回:
    - ExampleTable: 创建的项
    """
    try:
        db_item = ExampleTable(**data)
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return db_item
    except Exception as e:
        db.rollback()
        logger.error(f"创建示例项时出错: {e}")
        raise

def get_example_item(db: Session, item_id: int) -> Optional[ExampleTable]:
    """
    通过 ID 获取示例项
    
    参数:
    - db: 数据库会话
    - item_id: 项目ID
    
    返回:
    - Optional[ExampleTable]: 找到的项或None
    """
    return db.query(ExampleTable).filter(ExampleTable.id == item_id).first()

def get_example_items(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    active_only: bool = True
) -> List[ExampleTable]:
    """
    获取示例项列表
    
    参数:
    - db: 数据库会话
    - skip: 跳过的记录数
    - limit: 返回的记录数限制
    - active_only: 是否只返回活动状态的记录
    
    返回:
    - List[ExampleTable]: 示例项列表
    """
    query = db.query(ExampleTable)
    if active_only:
        query = query.filter(ExampleTable.active == True)
    return query.offset(skip).limit(limit).all()

def update_example_item(
    db: Session, 
    item_id: int, 
    data: Dict[str, Any]
) -> Optional[ExampleTable]:
    """
    更新示例项
    
    参数:
    - db: 数据库会话
    - item_id: 要更新的项目ID
    - data: 包含更新字段的字典
    
    返回:
    - Optional[ExampleTable]: 更新后的项或None（如果不存在）
    """
    try:
        db_item = get_example_item(db, item_id)
        if not db_item:
            return None
            
        for key, value in data.items():
            if hasattr(db_item, key):
                setattr(db_item, key, value)
        
        db.commit()
        db.refresh(db_item)
        return db_item
    except Exception as e:
        db.rollback()
        logger.error(f"更新示例项时出错: {e}")
        raise

def delete_example_item(db: Session, item_id: int) -> bool:
    """
    删除示例项
    
    参数:
    - db: 数据库会话
    - item_id: 要删除的项目ID
    
    返回:
    - bool: 操作是否成功
    """
    try:
        db_item = get_example_item(db, item_id)
        if not db_item:
            return False
            
        db.delete(db_item)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"删除示例项时出错: {e}")
        raise 