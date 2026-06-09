"""done 命令组 - 任务完成与推迟管理"""
import click
from datetime import date, datetime, timedelta

from ..storage import Storage
from ..models import StudyRecord
from ..utils import parse_date, format_duration


@click.group()
def done():
    """标记任务完成、记录学习时长、推迟任务"""
    pass


@done.command()
@click.argument("task_id")
@click.option("--duration", "-t", type=int, help="学习时长（分钟）")
@click.option("--hours", "-h", type=float, help="学习时长（小时），会转换为分钟")
def mark(task_id, duration, hours):
    """标记任务完成，并记录学习时长"""
    storage = Storage()
    task = storage.get_task(task_id)

    if not task:
        click.echo(f"错误：未找到任务 ID '{task_id}'")
        return

    if task.status == "done":
        click.echo(f"任务 '{task.title}' 已经标记为完成")
        confirm = click.confirm("要重新标记并更新学习时长吗？")
        if not confirm:
            return

    total_minutes = 0
    if duration:
        total_minutes += duration
    if hours:
        total_minutes += int(hours * 60)

    if total_minutes == 0:
        resp = click.prompt("请输入学习时长（分钟），或按 Enter 跳过", default="0")
        try:
            total_minutes = int(resp)
        except ValueError:
            total_minutes = 0

    task.status = "done"
    task.completed_at = datetime.now().isoformat()
    if total_minutes > 0:
        task.study_duration = total_minutes

    storage.update_task(task)

    if task.plan_item_id:
        plan_item = storage.get_plan_item(task.plan_item_id)
        if plan_item and plan_item.status != "completed":
            old_status = plan_item.status
            plan_item.status = "completed"
            storage.update_plan_item(plan_item)
            click.echo(f"  ℹ️ 关联计划项已更新: {old_status} → 已完成")

    if total_minutes > 0:
        record = StudyRecord(
            date=date.today().isoformat(),
            subject_id=task.subject_id,
            subject_name=task.subject_name,
            task_id=task.id,
            duration=total_minutes,
            task_title=task.title
        )
        storage.save_record(record)
        click.echo(f"✓ 已标记完成: {task.title}")
        click.echo(f"  学习时长: {format_duration(total_minutes)}")
    else:
        click.echo(f"✓ 已标记完成: {task.title}")


@done.command()
@click.argument("task_id")
@click.option("--to", "-t", default="tomorrow", help="推迟到的日期，默认明天")
@click.option("--days", "-d", type=int, help="推迟 N 天")
def postpone(task_id, to, days):
    """推迟未完成的任务到指定日期"""
    storage = Storage()
    task = storage.get_task(task_id)

    if not task:
        click.echo(f"错误：未找到任务 ID '{task_id}'")
        return

    if task.status == "done":
        click.echo(f"错误：任务 '{task.title}' 已完成，不能推迟")
        return

    if days:
        new_date = date.today() + timedelta(days=days)
    else:
        new_date = parse_date(to)
        if not new_date:
            click.echo(f"错误：无效的日期格式 '{to}'")
            return

    task.due_date = new_date.isoformat()
    task.status = "postponed"
    task.postponed_count += 1

    storage.update_task(task)

    click.echo(f"✓ 已推迟任务: {task.title}")
    click.echo(f"  新日期: {task.due_date}")
    click.echo(f"  推迟次数: {task.postponed_count}")


@done.command("postpone-all")
@click.option("--to", "-t", default="tomorrow", help="推迟到的日期")
@click.option("--days", "-d", type=int, help="推迟 N 天")
@click.option("--force", "-f", is_flag=True, help="不确认直接推迟")
def postpone_all(to, days, force):
    """批量推迟今日所有未完成的任务"""
    storage = Storage()
    today = date.today().isoformat()

    today_tasks = storage.get_tasks_by_date(today)
    pending_tasks = [t for t in today_tasks if t.status != "done"]

    if not pending_tasks:
        click.echo("今天没有未完成的任务需要推迟")
        return

    if not force:
        click.echo(f"将推迟以下 {len(pending_tasks)} 个任务:")
        for t in pending_tasks:
            click.echo(f"  - {t.title}")
        confirm = click.confirm("确认要推迟这些任务吗？")
        if not confirm:
            click.echo("已取消")
            return

    if days:
        new_date = date.today() + timedelta(days=days)
    else:
        new_date = parse_date(to)
        if not new_date:
            click.echo(f"错误：无效的日期格式 '{to}'")
            return

    for t in pending_tasks:
        t.due_date = new_date.isoformat()
        t.status = "postponed"
        t.postponed_count += 1
        storage.update_task(t)

    click.echo(f"✓ 已批量推迟 {len(pending_tasks)} 个任务到 {new_date.isoformat()}")


@done.command()
@click.argument("task_id")
@click.option("--duration", "-t", type=int, help="追加的学习时长（分钟）")
@click.option("--hours", "-h", type=float, help="追加的学习时长（小时）")
def addtime(task_id, duration, hours):
    """为已完成的任务追加学习时长"""
    storage = Storage()
    task = storage.get_task(task_id)

    if not task:
        click.echo(f"错误：未找到任务 ID '{task_id}'")
        return

    if task.status != "done":
        click.echo(f"警告：任务 '{task.title}' 尚未完成，将同时标记为完成")
        task.status = "done"
        task.completed_at = datetime.now().isoformat()

    total_minutes = 0
    if duration:
        total_minutes += duration
    if hours:
        total_minutes += int(hours * 60)

    if total_minutes == 0:
        resp = click.prompt("请输入要追加的学习时长（分钟）", default="30")
        try:
            total_minutes = int(resp)
        except ValueError:
            total_minutes = 30

    task.study_duration += total_minutes
    storage.update_task(task)

    record = StudyRecord(
        date=date.today().isoformat(),
        subject_id=task.subject_id,
        subject_name=task.subject_name,
        task_id=task.id,
        duration=total_minutes,
        task_title=task.title
    )
    storage.save_record(record)

    click.echo(f"✓ 已为任务 '{task.title}' 追加学习时长")
    click.echo(f"  本次追加: {format_duration(total_minutes)}")
    click.echo(f"  累计时长: {format_duration(task.study_duration)}")


@done.command()
@click.argument("task_id")
def undo(task_id):
    """取消任务完成标记，恢复为待完成状态"""
    storage = Storage()
    task = storage.get_task(task_id)

    if not task:
        click.echo(f"错误：未找到任务 ID '{task_id}'")
        return

    if task.status != "done":
        click.echo(f"任务 '{task.title}' 当前不是已完成状态")
        return

    deleted_records = storage.delete_records_by_task(task_id)
    old_duration = task.study_duration

    task.status = "pending"
    task.completed_at = None
    task.study_duration = 0
    storage.update_task(task)

    if task.plan_item_id:
        plan_item = storage.get_plan_item(task.plan_item_id)
        if plan_item and plan_item.status == "completed":
            plan_item.status = "converted"
            storage.update_plan_item(plan_item)
            click.echo(f"  ℹ️ 关联计划项已回退: 已完成 → 已转任务")

    click.echo(f"✓ 已取消完成标记: {task.title}")
    click.echo("  任务已恢复为待完成状态")
    if deleted_records > 0:
        click.echo(f"  已删除 {deleted_records} 条关联学习记录 ({format_duration(old_duration)})")
        click.echo("  今日总结、科目统计、连续学习天数会自动更新")


@done.command()
@click.option("--date", "-d", "date_str", help="查看指定日期的完成情况，默认今天")
def summary(date_str):
    """查看今日任务完成总结"""
    storage = Storage()

    if date_str:
        parsed = parse_date(date_str)
        if not parsed:
            click.echo(f"错误：无效的日期格式 '{date_str}'")
            return
        target_date = parsed.isoformat()
    else:
        target_date = date.today().isoformat()

    tasks = storage.get_tasks_by_date(target_date)
    records = storage.get_records_by_date(target_date)

    if not tasks and not records:
        click.echo(f"\n{target_date} 没有任务记录\n")
        return

    done_tasks = [t for t in tasks if t.status == "done"]
    pending_tasks = [t for t in tasks if t.status == "pending"]
    postponed_tasks = [t for t in tasks if t.status == "postponed"]

    total_duration = sum(r.duration for r in records)
    task_duration = sum(t.study_duration for t in done_tasks)

    click.echo(f"\n{'='*60}")
    click.echo(f"📊 {target_date} 学习总结")
    click.echo(f"{'='*60}")

    click.echo(f"\n任务完成情况:")
    click.echo(f"  ✅ 已完成: {len(done_tasks)} 个")
    click.echo(f"  ⏳ 待完成: {len(pending_tasks)} 个")
    click.echo(f"  ⏰ 已推迟: {len(postponed_tasks)} 个")

    total_tasks = len(tasks)
    if total_tasks > 0:
        completion_rate = (len(done_tasks) / total_tasks) * 100
        bar_length = 20
        filled = int(bar_length * completion_rate / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        click.echo(f"\n  完成率: [{bar}] {completion_rate:.1f}%")

    if total_duration > 0 or task_duration > 0:
        click.echo(f"\n学习时长统计:")
        if total_duration > 0:
            click.echo(f"  ⏱ 记录总时长: {format_duration(total_duration)}")
        if task_duration > 0:
            click.echo(f"  📝 任务累计时长: {format_duration(task_duration)}")

    if done_tasks:
        click.echo(f"\n✅ 今日完成的任务:")
        for t in done_tasks:
            duration_str = f" ({format_duration(t.study_duration)})" if t.study_duration > 0 else ""
            subject_str = f" [{t.subject_name}]" if t.subject_name else ""
            click.echo(f"  - {t.title}{subject_str}{duration_str}")

    if pending_tasks:
        click.echo(f"\n⏳ 今日未完成的任务:")
        for t in pending_tasks:
            subject_str = f" [{t.subject_name}]" if t.subject_name else ""
            click.echo(f"  - {t.title}{subject_str}")

    click.echo()
