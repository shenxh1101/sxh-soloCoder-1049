"""通用工具函数"""
from datetime import date, datetime, timedelta
from typing import List, Optional
from dateutil import parser as date_parser

from .storage import Storage
from .models import Task, Subject


def parse_date(date_str: str) -> Optional[date]:
    """解析日期字符串，支持多种格式"""
    try:
        if date_str.lower() == "today":
            return date.today()
        if date_str.lower() == "tomorrow":
            return date.today() + timedelta(days=1)
        return date_parser.parse(date_str).date()
    except (ValueError, TypeError):
        return None


def format_date(d: date) -> str:
    """格式化日期为字符串"""
    return d.isoformat()


def get_priority_label(priority: int) -> str:
    """获取优先级标签"""
    labels = {1: "高", 2: "中", 3: "低"}
    return labels.get(priority, "中")


def get_status_label(status: str) -> str:
    """获取状态标签"""
    labels = {
        "pending": "待完成",
        "done": "已完成",
        "postponed": "已推迟"
    }
    return labels.get(status, status)


def sort_tasks_by_priority(tasks: List[Task]) -> List[Task]:
    """按优先级排序任务，高优先级在前"""
    return sorted(tasks, key=lambda t: (t.priority, t.due_date))


def get_subject_by_name_or_id(storage: Storage, identifier: str, plan_id: Optional[str] = None) -> Optional[Subject]:
    """通过名称或 ID 获取科目，优先在指定/最新计划中查找"""
    subject = storage.get_subject(identifier)
    if subject:
        return subject

    target_plan_id = plan_id
    if not target_plan_id:
        active_plan = storage.get_active_plan()
        if active_plan:
            target_plan_id = active_plan.id

    if target_plan_id:
        plan_subjects = storage.get_subjects_by_plan(target_plan_id)
        for s in plan_subjects:
            if s.name.lower() == identifier.lower():
                return s

    subjects = storage.get_all_subjects()
    for s in subjects:
        if s.name.lower() == identifier.lower():
            return s
    return None


def get_subject_by_name_or_id_in_plan(storage: Storage, identifier: str, plan_id: str) -> Optional[Subject]:
    """仅在指定计划中通过名称或 ID 获取科目"""
    subject = storage.get_subject(identifier)
    if subject and subject.plan_id == plan_id:
        return subject

    plan_subjects = storage.get_subjects_by_plan(plan_id)
    for s in plan_subjects:
        if s.name.lower() == identifier.lower():
            return s
    return None


def calculate_days_remaining(exam_date_str: Optional[str]) -> Optional[int]:
    """计算距离考试的剩余天数"""
    if not exam_date_str:
        return None
    try:
        exam_date = date_parser.parse(exam_date_str).date()
        today = date.today()
        return (exam_date - today).days
    except (ValueError, TypeError):
        return None


def get_week_range(ref_date: Optional[date] = None) -> tuple:
    """获取参考日期所在周的起止日期"""
    if ref_date is None:
        ref_date = date.today()

    start = ref_date - timedelta(days=ref_date.weekday())
    end = start + timedelta(days=6)
    return start, end


def format_duration(minutes: int) -> str:
    """格式化时长显示"""
    if minutes < 60:
        return f"{minutes}分钟"
    hours = minutes // 60
    mins = minutes % 60
    if mins == 0:
        return f"{hours}小时"
    return f"{hours}小时{mins}分钟"


def get_progress_color(percentage: float) -> str:
    """根据进度百分比获取颜色代码（用于终端显示）"""
    if percentage >= 80:
        return "green"
    if percentage >= 50:
        return "yellow"
    return "red"
