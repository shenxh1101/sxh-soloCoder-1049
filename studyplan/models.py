"""数据模型定义"""
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from datetime import date, datetime
import uuid


def _generate_id() -> str:
    return uuid.uuid4().hex[:8]


@dataclass
class ExamPlan:
    """考试目标计划"""
    id: str = field(default_factory=_generate_id)
    name: str = ""
    exam_date: Optional[str] = None
    created_at: str = field(default_factory=lambda: date.today().isoformat())
    subjects: List[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


@dataclass
class Subject:
    """科目"""
    id: str = field(default_factory=_generate_id)
    name: str = ""
    plan_id: str = ""
    description: str = ""
    created_at: str = field(default_factory=lambda: date.today().isoformat())

    def to_dict(self):
        return asdict(self)


@dataclass
class Task:
    """每日任务"""
    id: str = field(default_factory=_generate_id)
    title: str = ""
    subject_id: Optional[str] = None
    subject_name: str = ""
    priority: int = 2  # 1: 高, 2: 中, 3: 低
    due_date: str = field(default_factory=lambda: date.today().isoformat())
    status: str = "pending"  # pending, done, postponed
    study_duration: int = 0  # 分钟
    completed_at: Optional[str] = None
    postponed_count: int = 0
    description: str = ""
    created_at: str = field(default_factory=lambda: date.today().isoformat())

    def to_dict(self):
        return asdict(self)


@dataclass
class ReviewItem:
    """错题/复习项"""
    id: str = field(default_factory=_generate_id)
    content: str = ""
    subject_id: Optional[str] = None
    subject_name: str = ""
    source: str = ""  # 来源：习题集、模拟卷等
    review_count: int = 0
    last_reviewed: Optional[str] = None
    next_review: str = field(default_factory=lambda: date.today().isoformat())
    mastery: int = 0  # 0-100 掌握程度
    notes: str = ""
    created_at: str = field(default_factory=lambda: date.today().isoformat())

    def to_dict(self):
        return asdict(self)


@dataclass
class StudyRecord:
    """学习记录，用于统计"""
    id: str = field(default_factory=_generate_id)
    date: str = field(default_factory=lambda: date.today().isoformat())
    subject_id: Optional[str] = None
    subject_name: str = ""
    task_id: Optional[str] = None
    duration: int = 0  # 分钟
    task_title: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self):
        return asdict(self)
