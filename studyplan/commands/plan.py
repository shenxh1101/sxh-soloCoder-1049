"""plan 命令组 - 考试目标和科目计划管理"""
import click
from tabulate import tabulate
from datetime import date

from ..storage import Storage
from ..models import ExamPlan, Subject
from ..utils import parse_date, calculate_days_remaining


@click.group()
def plan():
    """管理考试目标和科目计划"""
    pass


@plan.command()
@click.argument("name")
@click.option("--date", "-d", help="考试日期，格式：YYYY-MM-DD")
@click.option("--subjects", "-s", multiple=True, help="科目名称，可多次指定")
def create(name, date, subjects):
    """创建新的考试目标计划"""
    storage = Storage()

    exam_date = None
    if date:
        parsed = parse_date(date)
        if not parsed:
            click.echo(f"错误：无效的日期格式 '{date}'，请使用 YYYY-MM-DD 格式")
            return
        exam_date = parsed.isoformat()

    plan = ExamPlan(name=name, exam_date=exam_date)
    plan = storage.save_plan(plan)

    subject_list = []
    for subj_name in subjects:
        subject = Subject(name=subj_name, plan_id=plan.id)
        subject = storage.save_subject(subject)
        subject_list.append(subject)

    plan.subjects = [s.id for s in subject_list]
    storage.update_plan(plan)

    click.echo(f"✓ 已创建考试计划: {name}")
    if exam_date:
        days = calculate_days_remaining(exam_date)
        if days is not None:
            if days > 0:
                click.echo(f"  考试日期: {exam_date} (剩余 {days} 天)")
            elif days == 0:
                click.echo(f"  考试日期: {exam_date} (就是今天！)")
            else:
                click.echo(f"  考试日期: {exam_date} (已过 {-days} 天)")
    if subject_list:
        click.echo(f"  已添加科目: {', '.join(s.name for s in subject_list)}")
    click.echo(f"  计划 ID: {plan.id}")


@plan.command("set-date")
@click.argument("date_str")
@click.option("--plan-id", "-p", help="计划 ID，默认使用最新创建的计划")
def set_date(date_str, plan_id):
    """设置或修改考试日期"""
    storage = Storage()

    if plan_id:
        plan = storage.get_plan(plan_id)
    else:
        plan = storage.get_active_plan()

    if not plan:
        click.echo("错误：未找到考试计划，请先创建计划")
        return

    parsed = parse_date(date_str)
    if not parsed:
        click.echo(f"错误：无效的日期格式 '{date_str}'，请使用 YYYY-MM-DD 格式")
        return

    plan.exam_date = parsed.isoformat()
    storage.update_plan(plan)

    days = calculate_days_remaining(plan.exam_date)
    click.echo(f"✓ 已设置考试日期: {plan.exam_date}")
    if days is not None:
        if days > 0:
            click.echo(f"  距离考试还有 {days} 天，加油！")
        elif days == 0:
            click.echo(f"  考试就在今天！")
        else:
            click.echo(f"  考试已过去 {-days} 天")


@plan.command("add-subject")
@click.argument("name")
@click.option("--description", "-d", default="", help="科目描述")
@click.option("--plan-id", "-p", help="计划 ID，默认使用最新创建的计划")
def add_subject(name, description, plan_id):
    """添加科目到考试计划"""
    storage = Storage()

    if plan_id:
        plan = storage.get_plan(plan_id)
    else:
        plan = storage.get_active_plan()

    if not plan:
        click.echo("错误：未找到考试计划，请先创建计划")
        return

    subject = Subject(name=name, plan_id=plan.id, description=description)
    subject = storage.save_subject(subject)

    plan.subjects.append(subject.id)
    storage.update_plan(plan)

    click.echo(f"✓ 已添加科目: {name}")
    click.echo(f"  科目 ID: {subject.id}")
    if description:
        click.echo(f"  描述: {description}")


@plan.command("remove-subject")
@click.argument("identifier")
@click.option("--plan-id", "-p", help="计划 ID，默认使用最新创建的计划")
def remove_subject(identifier, plan_id):
    """从计划中移除科目（通过科目 ID 或名称）"""
    storage = Storage()

    if plan_id:
        plan = storage.get_plan(plan_id)
    else:
        plan = storage.get_active_plan()

    if not plan:
        click.echo("错误：未找到考试计划")
        return

    subject = storage.get_subject(identifier)
    if not subject:
        subjects = storage.get_subjects_by_plan(plan.id)
        for s in subjects:
            if s.name.lower() == identifier.lower():
                subject = s
                break

    if not subject:
        click.echo(f"错误：未找到科目 '{identifier}'")
        return

    if storage.delete_subject(subject.id):
        plan.subjects = [s for s in plan.subjects if s != subject.id]
        storage.update_plan(plan)
        click.echo(f"✓ 已移除科目: {subject.name}")
    else:
        click.echo(f"错误：移除科目失败")


@plan.command()
@click.option("--plan-id", "-p", help="计划 ID，默认显示最新创建的计划")
def show(plan_id):
    """显示考试计划详情"""
    storage = Storage()

    if plan_id:
        plan = storage.get_plan(plan_id)
    else:
        plan = storage.get_active_plan()

    if not plan:
        click.echo("尚未创建任何考试计划")
        click.echo("使用 'studyplan plan create <名称>' 创建第一个计划")
        return

    click.echo(f"\n{'='*50}")
    click.echo(f"📚 考试计划: {plan.name}")
    click.echo(f"{'='*50}")
    click.echo(f"  计划 ID: {plan.id}")
    click.echo(f"  创建时间: {plan.created_at}")

    if plan.exam_date:
        days = calculate_days_remaining(plan.exam_date)
        if days is not None:
            if days > 0:
                click.echo(f"  考试日期: {plan.exam_date} (剩余 {days} 天)")
            elif days == 0:
                click.echo(f"  考试日期: {plan.exam_date} (就是今天！)")
            else:
                click.echo(f"  考试日期: {plan.exam_date} (已过 {-days} 天)")
    else:
        click.echo(f"  考试日期: 未设置")
        click.echo(f"  使用 'studyplan plan set-date <日期>' 设置考试日期")

    subjects = storage.get_subjects_by_plan(plan.id)
    click.echo(f"\n  科目列表 ({len(subjects)} 个):")
    if subjects:
        table_data = []
        for s in subjects:
            table_data.append([s.id, s.name, s.description or "-"])
        click.echo(tabulate(table_data, headers=["ID", "科目", "描述"], tablefmt="simple"))
    else:
        click.echo("  暂无科目")
        click.echo("  使用 'studyplan plan add-subject <科目名>' 添加科目")
    click.echo()


@plan.command()
def list():
    """列出所有考试计划"""
    storage = Storage()
    plans = storage.get_all_plans()

    if not plans:
        click.echo("尚未创建任何考试计划")
        return

    table_data = []
    for p in plans:
        days = calculate_days_remaining(p.exam_date)
        days_str = f"{days}天" if days is not None and days > 0 else "已过期" if days is not None and days <= 0 else "未设置"
        subject_count = len(storage.get_subjects_by_plan(p.id))
        table_data.append([p.id, p.name, p.exam_date or "-", days_str, subject_count, p.created_at])

    click.echo(tabulate(table_data, headers=["ID", "名称", "考试日期", "剩余时间", "科目数", "创建时间"], tablefmt="simple"))


@plan.command()
@click.argument("plan_id")
@click.option("--force", "-f", is_flag=True, help="不确认直接删除")
def delete(plan_id, force):
    """删除考试计划"""
    storage = Storage()
    plan = storage.get_plan(plan_id)

    if not plan:
        click.echo(f"错误：未找到计划 ID '{plan_id}'")
        return

    if not force:
        confirm = click.confirm(f"确定要删除计划 '{plan.name}' 及其所有关联数据吗？")
        if not confirm:
            click.echo("已取消删除")
            return

    subjects = storage.get_subjects_by_plan(plan.id)
    for s in subjects:
        storage.delete_subject(s.id)

    if storage.delete_plan(plan.id):
        click.echo(f"✓ 已删除计划: {plan.name}")
    else:
        click.echo("错误：删除计划失败")


@plan.command("split")
@click.argument("subject_name")
@click.option("--tasks", "-t", multiple=True, help="拆分的任务名称，可多次指定")
@click.option("--plan-id", "-p", help="计划 ID，默认使用最新创建的计划")
def split_plan(subject_name, tasks, plan_id):
    """拆分科目的学习计划（添加任务模板）"""
    storage = Storage()

    if plan_id:
        plan = storage.get_plan(plan_id)
    else:
        plan = storage.get_active_plan()

    if not plan:
        click.echo("错误：未找到考试计划")
        return

    from ..utils import get_subject_by_name_or_id
    subject = get_subject_by_name_or_id(storage, subject_name)

    if not subject:
        subject = Subject(name=subject_name, plan_id=plan.id)
        subject = storage.save_subject(subject)
        plan.subjects.append(subject.id)
        storage.update_plan(plan)
        click.echo(f"✓ 已创建新科目: {subject_name}")

    click.echo(f"\n科目 '{subject.name}' 计划拆分:")
    for i, task_name in enumerate(tasks, 1):
        click.echo(f"  {i}. {task_name}")

    if tasks:
        click.echo(f"\n提示: 使用 'studyplan task add --subject {subject.name} <任务名>' 添加具体任务")
    else:
        click.echo("\n提示: 使用 --tasks 选项指定要拆分的任务，例如:")
        click.echo(f"  studyplan plan split {subject.name} --tasks \"第一轮复习\" --tasks \"第二轮复习\" --tasks \"模拟练习\"")
