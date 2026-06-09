"""task 命令组 - 每日任务管理"""
import click
from tabulate import tabulate
from datetime import date, timedelta

from ..storage import Storage
from ..models import Task
from ..utils import (
    parse_date, get_priority_label, get_status_label,
    sort_tasks_by_priority, get_subject_by_name_or_id
)


@click.group()
def task():
    """管理每日学习任务"""
    pass


@task.command()
@click.argument("title")
@click.option("--subject", "-s", help="科目名称或 ID")
@click.option("--priority", "-p", type=click.Choice(['1', '2', '3', 'high', 'medium', 'low']),
              default='2', help="优先级: 1/high(高), 2/medium(中), 3/low(低)，默认中")
@click.option("--date", "-d", default="today", help="任务日期，默认今天")
@click.option("--description", "-m", default="", help="任务描述")
def add(title, subject, priority, date, description):
    """添加新的每日任务"""
    storage = Storage()

    priority_map = {'1': 1, 'high': 1, '2': 2, 'medium': 2, '3': 3, 'low': 3}
    priority_int = priority_map[priority]

    parsed_date = parse_date(date)
    if not parsed_date:
        click.echo(f"错误：无效的日期格式 '{date}'")
        return

    subject_id = None
    subject_name = ""
    if subject:
        active_plan = storage.get_active_plan()
        plan_id = active_plan.id if active_plan else None
        subj = get_subject_by_name_or_id(storage, subject, plan_id)
        if subj:
            subject_id = subj.id
            subject_name = subj.name
            if plan_id and subj.plan_id == plan_id:
                click.echo(f"  关联科目: {subj.name} (来自当前计划)")
            else:
                click.echo(f"  关联科目: {subj.name} (来自其他计划)")
        else:
            click.echo(f"警告：未找到科目 '{subject}'，任务将不关联科目")

    task = Task(
        title=title,
        subject_id=subject_id,
        subject_name=subject_name,
        priority=priority_int,
        due_date=parsed_date.isoformat(),
        description=description
    )
    task = storage.save_task(task)

    click.echo(f"✓ 已添加任务: {title}")
    click.echo(f"  任务 ID: {task.id}")
    if subject_name:
        click.echo(f"  科目: {subject_name}")
    click.echo(f"  优先级: {get_priority_label(priority_int)}")
    click.echo(f"  日期: {task.due_date}")


@task.command()
@click.option("--date", "-d", "date_str", help="指定日期，默认今天")
@click.option("--all", "-a", is_flag=True, help="显示所有日期的任务")
@click.option("--subject", "-s", help="按科目筛选")
@click.option("--sort-by-priority", "sort_priority", is_flag=True, default=True, help="按优先级排序（默认）")
@click.option("--no-sort", is_flag=True, help="不排序，按添加顺序显示")
def list(date_str, all, subject, sort_priority, no_sort):
    """列出任务清单（今日清单）"""
    storage = Storage()

    if all:
        tasks = storage.get_all_tasks()
    elif date_str:
        parsed = parse_date(date_str)
        if not parsed:
            click.echo(f"错误：无效的日期格式 '{date_str}'")
            return
        tasks = storage.get_tasks_by_date(parsed.isoformat())
    else:
        today = date.today().isoformat()
        tasks_dict = {}
        for t in storage.get_tasks_by_date(today):
            tasks_dict[t.id] = t
        for t in storage.get_all_tasks():
            if t.status == "postponed" and t.due_date <= today:
                if t.id not in tasks_dict:
                    tasks_dict[t.id] = t
        tasks = [*tasks_dict.values()]

    if subject:
        active_plan = storage.get_active_plan()
        plan_id = active_plan.id if active_plan else None
        subj = get_subject_by_name_or_id(storage, subject, plan_id)
        if subj:
            tasks = [t for t in tasks if t.subject_id == subj.id]
        else:
            click.echo(f"警告：未找到科目 '{subject}'")

    if not no_sort and sort_priority:
        tasks = sort_tasks_by_priority(tasks)

    if not tasks:
        date_display = "所有日期" if all else (date_str or "今天")
        click.echo(f"{date_display} 暂无任务")
        click.echo("使用 'studyplan task add <任务名>' 添加新任务")
        return

    date_display = "所有日期" if all else (date_str or "今天")
    click.echo(f"\n📋 {date_display} 任务清单 ({len(tasks)} 个任务)")
    click.echo("-" * 70)

    table_data = []
    for t in tasks:
        status_icon = "✅" if t.status == "done" else "⏰" if t.status == "postponed" else "⬜"
        priority_str = get_priority_label(t.priority)
        priority_color = "red" if t.priority == 1 else "yellow" if t.priority == 2 else "white"
        status_str = get_status_label(t.status)
        subject_display = t.subject_name or "-"
        duration_display = f"{t.study_duration}分钟" if t.study_duration > 0 else "-"

        table_data.append([
            t.id,
            status_icon,
            click.style(priority_str, fg=priority_color),
            subject_display,
            t.title,
            status_str,
            duration_display,
            t.due_date
        ])

    click.echo(tabulate(
        table_data,
        headers=["ID", "状态", "优先级", "科目", "任务", "状态", "学习时长", "日期"],
        tablefmt="simple",
        colalign=["left", "center", "center", "left", "left", "left", "right", "left"]
    ))

    done_count = sum(1 for t in tasks if t.status == "done")
    pending_count = sum(1 for t in tasks if t.status == "pending")
    postponed_count = sum(1 for t in tasks if t.status == "postponed")
    total_duration = sum(t.study_duration for t in tasks)

    click.echo("\n📊 统计:")
    click.echo(f"  已完成: {done_count} | 待完成: {pending_count} | 已推迟: {postponed_count}")
    if total_duration > 0:
        hours = total_duration // 60
        mins = total_duration % 60
        if hours > 0:
            click.echo(f"  总学习时长: {hours}小时{mins}分钟")
        else:
            click.echo(f"  总学习时长: {mins}分钟")
    click.echo()


@task.command()
@click.argument("task_id")
def show(task_id):
    """显示任务详情"""
    storage = Storage()
    task = storage.get_task(task_id)

    if not task:
        click.echo(f"错误：未找到任务 ID '{task_id}'")
        return

    click.echo(f"\n{'='*50}")
    click.echo(f"📝 任务详情")
    click.echo(f"{'='*50}")
    click.echo(f"  任务 ID: {task.id}")
    click.echo(f"  标题: {task.title}")
    click.echo(f"  科目: {task.subject_name or '未设置'}")
    click.echo(f"  优先级: {get_priority_label(task.priority)}")
    click.echo(f"  状态: {get_status_label(task.status)}")
    click.echo(f"  日期: {task.due_date}")
    if task.study_duration > 0:
        click.echo(f"  学习时长: {task.study_duration} 分钟")
    if task.completed_at:
        click.echo(f"  完成时间: {task.completed_at}")
    if task.postponed_count > 0:
        click.echo(f"  推迟次数: {task.postponed_count}")
    if task.description:
        click.echo(f"  描述: {task.description}")
    click.echo(f"  创建时间: {task.created_at}")
    click.echo()


@task.command()
@click.argument("task_id")
@click.option("--title", "-t", help="修改任务标题")
@click.option("--subject", "-s", help="修改关联科目")
@click.option("--priority", "-p", type=click.Choice(['1', '2', '3', 'high', 'medium', 'low']),
              help="修改优先级")
@click.option("--date", "-d", help="修改任务日期")
@click.option("--description", "-m", help="修改任务描述")
def edit(task_id, title, subject, priority, date, description):
    """编辑任务"""
    storage = Storage()
    task = storage.get_task(task_id)

    if not task:
        click.echo(f"错误：未找到任务 ID '{task_id}'")
        return

    if title:
        task.title = title

    if subject:
        if subject.lower() == "none":
            task.subject_id = None
            task.subject_name = ""
        else:
            active_plan = storage.get_active_plan()
            plan_id = active_plan.id if active_plan else None
            subj = get_subject_by_name_or_id(storage, subject, plan_id)
            if subj:
                task.subject_id = subj.id
                task.subject_name = subj.name
            else:
                click.echo(f"警告：未找到科目 '{subject}'，保持原科目不变")

    if priority:
        priority_map = {'1': 1, 'high': 1, '2': 2, 'medium': 2, '3': 3, 'low': 3}
        task.priority = priority_map[priority]

    if date:
        parsed = parse_date(date)
        if parsed:
            task.due_date = parsed.isoformat()
        else:
            click.echo(f"警告：无效的日期格式 '{date}'，保持原日期不变")

    if description:
        task.description = description

    storage.update_task(task)
    click.echo(f"✓ 已更新任务: {task.title}")


@task.command()
@click.argument("task_id")
@click.option("--force", "-f", is_flag=True, help="不确认直接删除")
def remove(task_id, force):
    """删除任务"""
    storage = Storage()
    task = storage.get_task(task_id)

    if not task:
        click.echo(f"错误：未找到任务 ID '{task_id}'")
        return

    if not force:
        confirm = click.confirm(f"确定要删除任务 '{task.title}' 吗？")
        if not confirm:
            click.echo("已取消删除")
            return

    if storage.delete_task(task_id):
        click.echo(f"✓ 已删除任务: {task.title}")
    else:
        click.echo("错误：删除任务失败")


@task.command("today")
def today_tasks():
    """生成今日任务清单（待完成 + 推迟的）"""
    storage = Storage()
    today = date.today().isoformat()

    tasks_dict = {}
    for t in storage.get_tasks_by_date(today):
        tasks_dict[t.id] = t
    for t in storage.get_all_tasks():
        if t.status == "postponed" and t.due_date <= today:
            if t.id not in tasks_dict:
                tasks_dict[t.id] = t

    all_tasks = [*tasks_dict.values()]
    all_tasks = sort_tasks_by_priority(all_tasks)

    if not all_tasks:
        click.echo("\n🎉 今天没有待完成的任务！")
        click.echo("使用 'studyplan task add <任务名>' 添加新任务\n")
        return

    click.echo(f"\n{'='*60}")
    click.echo(f"📅 今日学习清单 - {today}")
    click.echo(f"{'='*60}")

    high_tasks = [t for t in all_tasks if t.priority == 1 and t.status != "done"]
    medium_tasks = [t for t in all_tasks if t.priority == 2 and t.status != "done"]
    low_tasks = [t for t in all_tasks if t.priority == 3 and t.status != "done"]
    done_tasks = [t for t in all_tasks if t.status == "done"]

    def print_task_group(title, tasks, icon):
        if tasks:
            click.echo(f"\n{icon} {title} ({len(tasks)}):")
            for i, t in enumerate(tasks, 1):
                postponed_tag = " [已推迟]" if t.status == "postponed" else ""
                subject_tag = f" ({t.subject_name})" if t.subject_name else ""
                click.echo(f"  {i}. [{t.id}] {t.title}{subject_tag}{postponed_tag}")

    print_task_group("高优先级", high_tasks, "🔴")
    print_task_group("中优先级", medium_tasks, "🟡")
    print_task_group("低优先级", low_tasks, "🟢")

    if done_tasks:
        click.echo(f"\n✅ 已完成 ({len(done_tasks)}):")
        for t in done_tasks:
            subject_tag = f" ({t.subject_name})" if t.subject_name else ""
            click.echo(f"  - {t.title}{subject_tag}")

    total_pending = len(high_tasks) + len(medium_tasks) + len(low_tasks)
    total_done = len(done_tasks)
    click.echo(f"\n📊 进度: {total_done}/{total_pending + total_done} 任务已完成")
    if total_pending + total_done > 0:
        progress = (total_done / (total_pending + total_done)) * 100
        click.echo(f"    完成率: {progress:.1f}%")
    click.echo()


@task.command("pending")
def pending_tasks():
    """列出所有待完成的任务"""
    storage = Storage()
    tasks = storage.get_pending_tasks()
    tasks = sort_tasks_by_priority(tasks)

    if not tasks:
        click.echo("\n🎉 没有待完成的任务！继续保持！\n")
        return

    click.echo(f"\n{'='*60}")
    click.echo(f"⏰ 待完成任务 ({len(tasks)} 个)")
    click.echo(f"{'='*60}")

    table_data = []
    for t in tasks:
        table_data.append([
            t.id,
            get_priority_label(t.priority),
            t.subject_name or "-",
            t.title,
            t.due_date,
            t.postponed_count if t.postponed_count > 0 else 0
        ])

    click.echo(tabulate(
        table_data,
        headers=["ID", "优先级", "科目", "任务", "截止日期", "推迟次数"],
        tablefmt="simple"
    ))
    click.echo()
