"""数据存储模块，使用 JSON 文件持久化"""
import json
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import date, timedelta

from .models import ExamPlan, Subject, Task, ReviewItem, StudyRecord, PlanItem


class Storage:
    """JSON 文件存储管理器"""

    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            home = Path.home()
            data_dir = home / ".studyplan"
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._init_files()

    def _init_files(self):
        """初始化数据文件"""
        files = ["plans.json", "subjects.json", "tasks.json", "reviews.json", "records.json", "plan_items.json"]
        for f in files:
            file_path = self.data_dir / f
            if not file_path.exists():
                self._write_json(file_path, [])

    def _read_json(self, file_path: Path) -> List[Dict[str, Any]]:
        """读取 JSON 文件"""
        if not file_path.exists():
            return []
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _write_json(self, file_path: Path, data: List[Dict[str, Any]]):
        """写入 JSON 文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # -------- ExamPlan 相关操作 --------

    def save_plan(self, plan: ExamPlan) -> ExamPlan:
        plans = self._read_json(self.data_dir / "plans.json")
        plans.append(plan.to_dict())
        self._write_json(self.data_dir / "plans.json", plans)
        return plan

    def update_plan(self, plan: ExamPlan) -> Optional[ExamPlan]:
        plans = self._read_json(self.data_dir / "plans.json")
        for i, p in enumerate(plans):
            if p["id"] == plan.id:
                plans[i] = plan.to_dict()
                self._write_json(self.data_dir / "plans.json", plans)
                return plan
        return None

    def get_plan(self, plan_id: str) -> Optional[ExamPlan]:
        plans = self._read_json(self.data_dir / "plans.json")
        for p in plans:
            if p["id"] == plan_id:
                return ExamPlan(**p)
        return None

    def get_all_plans(self) -> List[ExamPlan]:
        plans = self._read_json(self.data_dir / "plans.json")
        return [ExamPlan(**p) for p in plans]

    def get_active_plan(self) -> Optional[ExamPlan]:
        plans = self.get_all_plans()
        if not plans:
            return None
        plans_sorted = sorted(plans, key=lambda p: (p.created_at, p.id), reverse=True)
        return plans_sorted[0] if plans_sorted else None

    def delete_plan(self, plan_id: str) -> bool:
        plans = self._read_json(self.data_dir / "plans.json")
        new_plans = [p for p in plans if p["id"] != plan_id]
        if len(new_plans) == len(plans):
            return False
        self._write_json(self.data_dir / "plans.json", new_plans)
        return True

    # -------- Subject 相关操作 --------

    def save_subject(self, subject: Subject) -> Subject:
        subjects = self._read_json(self.data_dir / "subjects.json")
        subjects.append(subject.to_dict())
        self._write_json(self.data_dir / "subjects.json", subjects)
        return subject

    def update_subject(self, subject: Subject) -> Optional[Subject]:
        subjects = self._read_json(self.data_dir / "subjects.json")
        for i, s in enumerate(subjects):
            if s["id"] == subject.id:
                subjects[i] = subject.to_dict()
                self._write_json(self.data_dir / "subjects.json", subjects)
                return subject
        return None

    def get_subject(self, subject_id: str) -> Optional[Subject]:
        subjects = self._read_json(self.data_dir / "subjects.json")
        for s in subjects:
            if s["id"] == subject_id:
                return Subject(**s)
        return None

    def get_subjects_by_plan(self, plan_id: str) -> List[Subject]:
        subjects = self._read_json(self.data_dir / "subjects.json")
        return [Subject(**s) for s in subjects if s["plan_id"] == plan_id]

    def get_all_subjects(self) -> List[Subject]:
        subjects = self._read_json(self.data_dir / "subjects.json")
        return [Subject(**s) for s in subjects]

    def delete_subject(self, subject_id: str) -> bool:
        subjects = self._read_json(self.data_dir / "subjects.json")
        new_subjects = [s for s in subjects if s["id"] != subject_id]
        if len(new_subjects) == len(subjects):
            return False
        self._write_json(self.data_dir / "subjects.json", new_subjects)
        return True

    # -------- Task 相关操作 --------

    def save_task(self, task: Task) -> Task:
        tasks = self._read_json(self.data_dir / "tasks.json")
        tasks.append(task.to_dict())
        self._write_json(self.data_dir / "tasks.json", tasks)
        return task

    def update_task(self, task: Task) -> Optional[Task]:
        tasks = self._read_json(self.data_dir / "tasks.json")
        for i, t in enumerate(tasks):
            if t["id"] == task.id:
                tasks[i] = task.to_dict()
                self._write_json(self.data_dir / "tasks.json", tasks)
                return task
        return None

    def get_task(self, task_id: str) -> Optional[Task]:
        tasks = self._read_json(self.data_dir / "tasks.json")
        for t in tasks:
            if t["id"] == task_id:
                return Task(**t)
        return None

    def get_tasks_by_date(self, target_date: str) -> List[Task]:
        tasks = self._read_json(self.data_dir / "tasks.json")
        return [Task(**t) for t in tasks if t["due_date"] == target_date]

    def get_tasks_by_subject(self, subject_id: str) -> List[Task]:
        tasks = self._read_json(self.data_dir / "tasks.json")
        return [Task(**t) for t in tasks if t["subject_id"] == subject_id]

    def get_pending_tasks(self) -> List[Task]:
        tasks = self._read_json(self.data_dir / "tasks.json")
        today = date.today().isoformat()
        return [Task(**t) for t in tasks if t["status"] == "pending" and t["due_date"] <= today]

    def get_all_tasks(self) -> List[Task]:
        tasks = self._read_json(self.data_dir / "tasks.json")
        return [Task(**t) for t in tasks]

    def delete_task(self, task_id: str) -> bool:
        tasks = self._read_json(self.data_dir / "tasks.json")
        new_tasks = [t for t in tasks if t["id"] != task_id]
        if len(new_tasks) == len(tasks):
            return False
        self._write_json(self.data_dir / "tasks.json", new_tasks)
        return True

    # -------- ReviewItem 相关操作 --------

    def save_review(self, review: ReviewItem) -> ReviewItem:
        reviews = self._read_json(self.data_dir / "reviews.json")
        reviews.append(review.to_dict())
        self._write_json(self.data_dir / "reviews.json", reviews)
        return review

    def update_review(self, review: ReviewItem) -> Optional[ReviewItem]:
        reviews = self._read_json(self.data_dir / "reviews.json")
        for i, r in enumerate(reviews):
            if r["id"] == review.id:
                reviews[i] = review.to_dict()
                self._write_json(self.data_dir / "reviews.json", reviews)
                return review
        return None

    def get_review(self, review_id: str) -> Optional[ReviewItem]:
        reviews = self._read_json(self.data_dir / "reviews.json")
        for r in reviews:
            if r["id"] == review_id:
                return ReviewItem(**r)
        return None

    def get_reviews_due(self, target_date: Optional[str] = None) -> List[ReviewItem]:
        if target_date is None:
            target_date = date.today().isoformat()
        reviews = self._read_json(self.data_dir / "reviews.json")
        return [ReviewItem(**r) for r in reviews if r["next_review"] <= target_date]

    def get_reviews_by_subject(self, subject_id: str) -> List[ReviewItem]:
        reviews = self._read_json(self.data_dir / "reviews.json")
        return [ReviewItem(**r) for r in reviews if r["subject_id"] == subject_id]

    def get_all_reviews(self) -> List[ReviewItem]:
        reviews = self._read_json(self.data_dir / "reviews.json")
        return [ReviewItem(**r) for r in reviews]

    def delete_review(self, review_id: str) -> bool:
        reviews = self._read_json(self.data_dir / "reviews.json")
        new_reviews = [r for r in reviews if r["id"] != review_id]
        if len(new_reviews) == len(reviews):
            return False
        self._write_json(self.data_dir / "reviews.json", new_reviews)
        return True

    # -------- StudyRecord 相关操作 --------

    def save_record(self, record: StudyRecord) -> StudyRecord:
        records = self._read_json(self.data_dir / "records.json")
        records.append(record.to_dict())
        self._write_json(self.data_dir / "records.json", records)
        return record

    def get_records_by_date(self, target_date: str) -> List[StudyRecord]:
        records = self._read_json(self.data_dir / "records.json")
        return [StudyRecord(**r) for r in records if r["date"] == target_date]

    def get_records_by_date_range(self, start_date: str, end_date: str) -> List[StudyRecord]:
        records = self._read_json(self.data_dir / "records.json")
        return [StudyRecord(**r) for r in records if start_date <= r["date"] <= end_date]

    def get_records_by_subject(self, subject_id: str) -> List[StudyRecord]:
        records = self._read_json(self.data_dir / "records.json")
        return [StudyRecord(**r) for r in records if r["subject_id"] == subject_id]

    def get_all_records(self) -> List[StudyRecord]:
        records = self._read_json(self.data_dir / "records.json")
        return [StudyRecord(**r) for r in records]

    def get_study_dates(self) -> List[str]:
        """获取所有有学习记录的日期列表"""
        records = self._read_json(self.data_dir / "records.json")
        dates = sorted(set(r["date"] for r in records))
        return dates

    def get_streak(self) -> int:
        """计算连续学习天数"""
        dates = self.get_study_dates()
        if not dates:
            return 0

        today = date.today()
        streak = 0
        current_date = today

        while True:
            date_str = current_date.isoformat()
            if date_str in dates:
                streak += 1
                current_date -= timedelta(days=1)
            else:
                break

        return streak

    def delete_record(self, record_id: str) -> bool:
        """删除学习记录"""
        records = self._read_json(self.data_dir / "records.json")
        new_records = [r for r in records if r["id"] != record_id]
        if len(new_records) == len(records):
            return False
        self._write_json(self.data_dir / "records.json", new_records)
        return True

    def delete_records_by_task(self, task_id: str) -> int:
        """删除指定任务的所有学习记录，返回删除的记录数"""
        records = self._read_json(self.data_dir / "records.json")
        deleted_count = 0
        new_records = []
        for r in records:
            if r.get("task_id") == task_id:
                deleted_count += 1
            else:
                new_records.append(r)
        if deleted_count > 0:
            self._write_json(self.data_dir / "records.json", new_records)
        return deleted_count

    # -------- PlanItem 相关操作 --------

    def save_plan_item(self, item: PlanItem) -> PlanItem:
        """保存科目拆分计划项"""
        items = self._read_json(self.data_dir / "plan_items.json")
        items.append(item.to_dict())
        self._write_json(self.data_dir / "plan_items.json", items)
        return item

    def update_plan_item(self, item: PlanItem) -> Optional[PlanItem]:
        """更新科目拆分计划项"""
        items = self._read_json(self.data_dir / "plan_items.json")
        for i, it in enumerate(items):
            if it["id"] == item.id:
                items[i] = item.to_dict()
                self._write_json(self.data_dir / "plan_items.json", items)
                return item
        return None

    def get_plan_item(self, item_id: str) -> Optional[PlanItem]:
        """获取单个计划项"""
        items = self._read_json(self.data_dir / "plan_items.json")
        for it in items:
            if it["id"] == item_id:
                return PlanItem(**it)
        return None

    def get_plan_items_by_subject(self, subject_id: str) -> List[PlanItem]:
        """获取指定科目的所有计划项"""
        items = self._read_json(self.data_dir / "plan_items.json")
        result = [PlanItem(**it) for it in items if it["subject_id"] == subject_id]
        return sorted(result, key=lambda x: (x.order, x.created_at))

    def get_plan_items_by_plan(self, plan_id: str) -> List[PlanItem]:
        """获取指定计划的所有计划项"""
        items = self._read_json(self.data_dir / "plan_items.json")
        result = [PlanItem(**it) for it in items if it["plan_id"] == plan_id]
        return sorted(result, key=lambda x: (x.order, x.created_at))

    def get_all_plan_items(self) -> List[PlanItem]:
        """获取所有计划项"""
        items = self._read_json(self.data_dir / "plan_items.json")
        return [PlanItem(**it) for it in items]

    def delete_plan_item(self, item_id: str) -> bool:
        """删除计划项"""
        items = self._read_json(self.data_dir / "plan_items.json")
        new_items = [it for it in items if it["id"] != item_id]
        if len(new_items) == len(items):
            return False
        self._write_json(self.data_dir / "plan_items.json", new_items)
        return True

    def delete_plan_items_by_subject(self, subject_id: str) -> int:
        """删除指定科目的所有计划项，返回删除数量"""
        items = self._read_json(self.data_dir / "plan_items.json")
        new_items = [it for it in items if it["subject_id"] != subject_id]
        deleted = len(items) - len(new_items)
        if deleted > 0:
            self._write_json(self.data_dir / "plan_items.json", new_items)
        return deleted
