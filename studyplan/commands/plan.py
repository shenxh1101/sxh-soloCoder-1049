"""plan 命令组 - 考试目标和科目计划管理"""
import click
from tabulate import tabulate
from datetime import date, timedelta

from ..storage import Storage
from ..models import ExamPlan, Subject, PlanItem, Task
from ..utils import parse_date, calculate_days_remaining, get_priority_label


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

    deleted_items = storage.delete_plan_items_by_subject(subject.id)
    if storage.delete_subject(subject.id):
        plan.subjects = [s for s in plan.subjects if s != subject.id]
        storage.update_plan(plan)
        click.echo(f"✓ 已移除科目: {subject.name}")
        if deleted_items > 0:
            click.echo(f"  同时删除了 {deleted_items} 个关联的计划项")
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
    all_tasks = storage.get_all_tasks()
    task_by_item_id = {t.plan_item_id: t for t in all_tasks if t.plan_item_id}

    click.echo(f"\n  科目列表 ({len(subjects)} 个):")
    if subjects:
        for s in subjects:
            click.echo(f"\n  📖 {s.name} (ID: {s.id})" + (f" - {s.description}" if s.description else ""))
            items = storage.get_plan_items_by_subject(s.id)
            if items:
                total = len(items)
                pending = sum(1 for i in items if i.status == "pending")
                in_progress = sum(1 for i in items if i.status == "in_progress")
                completed = sum(1 for i in items if i.status == "completed")
                converted = sum(1 for i in items if i.status == "converted")
                converted_done = sum(
                    1 for i in items
                    if i.status == "converted"
                    and i.id in task_by_item_id
                    and task_by_item_id[i.id].status == "done"
                )
                progress = completed + converted_done
                progress_pct = (progress / total * 100) if total > 0 else 0

                click.echo(f"    进度: {progress}/{total} ({progress_pct:.0f}%)"
                           f" | 待开始:{pending} 进行中:{in_progress} 已完成:{completed}"
                           f" | 已转任务:{converted} (其中已完成:{converted_done})")

                click.echo(f"    拆分计划 ({len(items)} 项):")
                table_data = []
                for it in items:
                    priority_str = get_priority_label(it.priority)
                    status_map = {
                        "pending": "待开始",
                        "in_progress": "进行中",
                        "completed": "已完成",
                        "converted": "已转任务"
                    }
                    status_str = status_map.get(it.status, it.status)
                    if it.status == "converted" and it.id in task_by_item_id:
                        task_status = task_by_item_id[it.id].status
                        if task_status == "done":
                            status_str = "✓ 任务已完成"
                        elif task_status == "postponed":
                            status_str = "⏳ 任务已推迟"
                        else:
                            status_str = "📋 任务待完成"
                    date_str = it.expected_date or "-"
                    table_data.append([
                        it.id,
                        priority_str,
                        it.title,
                        status_str,
                        date_str,
                        it.notes or "-"
                    ])
                click.echo(tabulate(
                    table_data,
                    headers=["ID", "优先级", "计划项", "状态", "预计日期", "备注"],
                    tablefmt="simple",
                    showindex=False
                ))
            else:
                click.echo("    暂无拆分计划")
                click.echo(f"    使用 'studyplan plan split {s.name} --tasks \"任务名\" 添加")
    else:
        click.echo("  暂无科目")
        click.echo("  使用 'studyplan plan add-subject <科目名>' 添加科目")
    click.echo()


@plan.command()
@click.option("--plan-id", "-p", help="计划 ID，默认显示最新创建的计划")
def progress(plan_id):
    """显示各科目进度统计"""
    storage = Storage()

    if plan_id:
        plan = storage.get_plan(plan_id)
    else:
        plan = storage.get_active_plan()

    if not plan:
        click.echo("尚未创建任何考试计划")
        click.echo("使用 'studyplan plan create <名称>' 创建第一个计划")
        return

    from ..utils import format_duration, get_progress_color

    subjects = storage.get_subjects_by_plan(plan.id)
    all_tasks = storage.get_all_tasks()
    all_records = storage.get_all_records()
    task_by_item_id = {t.plan_item_id: t for t in all_tasks if t.plan_item_id}
    task_durations = {}
    for r in all_records:
        if r.task_id in task_durations:
            task_durations[r.task_id] += r.duration
        else:
            task_durations[r.task_id] = r.duration

    click.echo(f"\n{'='*60}")
    click.echo(f"📊 学习进度统计 - {plan.name}")
    click.echo(f"{'='*60}")

    if not subjects:
        click.echo("\n  暂无科目")
        click.echo("  使用 'studyplan plan add-subject <科目名>' 添加科目")
        click.echo()
        return

    table_data = []
    total_all = 0
    progress_all = 0
    total_study_time = 0

    for s in subjects:
        items = storage.get_plan_items_by_subject(s.id)
        total = len(items)
        total_all += total

        pending = sum(1 for i in items if i.status == "pending")
        in_progress = sum(1 for i in items if i.status == "in_progress")
        completed = sum(1 for i in items if i.status == "completed")
        converted = sum(1 for i in items if i.status == "converted")
        converted_done = sum(
            1 for i in items
            if i.status == "converted"
            and i.id in task_by_item_id
            and task_by_item_id[i.id].status == "done"
        )

        progress = completed + converted_done
        progress_all += progress
        progress_pct = (progress / total * 100) if total > 0 else 0

        subject_tasks = [t for t in all_tasks if t.subject_id == s.id]
        subject_duration = sum(task_durations.get(t.id, 0) for t in subject_tasks)
        total_study_time += subject_duration

        color = get_progress_color(progress_pct)
        progress_bar = "█" * int(progress_pct / 10) + "░" * (10 - int(progress_pct / 10))

        table_data.append([
            s.name,
            total,
            pending,
            in_progress,
            completed,
            f"{converted}({converted_done}✓)",
            f"{progress}/{total}",
            f"{progress_bar} {progress_pct:.0f}%",
            format_duration(subject_duration) if subject_duration > 0 else "-"
        ])

    click.echo(f"\n{'='*60}")
    click.echo(tabulate(
        table_data,
        headers=["科目", "总计", "待开始", "进行中", "已完成", "已转任务", "进度", "完成率", "学习时长"],
        tablefmt="simple",
        showindex=False
    ))
    click.echo(f"{'='*60}")

    overall_pct = (progress_all / total_all * 100) if total_all > 0 else 0
    click.echo(f"\n  总体进度: {progress_all}/{total_all} ({overall_pct:.0f}%)")
    click.echo(f"  总学习时长: {format_duration(total_study_time)}")
    click.echo()
    click.echo("  使用 'studyplan plan show' 查看详细计划项")
    click.echo("  使用 'studyplan stats subject' 查看详细科目统计")
    click.echo()


@plan.command()
def list():
    """列出所有考试计划（按创建时间新到旧排序）"""
    storage = Storage()
    plans = storage.get_all_plans()

    if not plans:
        click.echo("尚未创建任何考试计划")
        return

    plans_sorted = sorted(plans, key=lambda p: p.created_at, reverse=True)

    table_data = []
    for p in plans_sorted:
        days = calculate_days_remaining(p.exam_date)
        days_str = f"{days}天" if days is not None and days > 0 else "已过期" if days is not None and days <= 0 else "未设置"
        subject_count = len(storage.get_subjects_by_plan(p.id))
        active_marker = " [当前]" if p.id == plans_sorted[0].id else ""
        table_data.append([p.id, p.name + active_marker, p.exam_date or "-", days_str, subject_count, p.created_at])

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
    total_items = 0
    for s in subjects:
        total_items += storage.delete_plan_items_by_subject(s.id)
        storage.delete_subject(s.id)

    if storage.delete_plan(plan.id):
        click.echo(f"✓ 已删除计划: {plan.name}")
        if total_items > 0:
            click.echo(f"  同时删除了 {total_items} 个计划项和 {len(subjects)} 个科目")
    else:
        click.echo("错误：删除计划失败")


@plan.command("split")
@click.argument("subject_name")
@click.option("--tasks", "-t", multiple=True, help="拆分的任务名称，可多次指定")
@click.option("--priority", "-p", type=click.Choice(['1', '2', '3', 'high', 'medium', 'low']),
              default='2', help="优先级，默认中")
@click.option("--date", "-d", "date_str", help="预计完成日期")
@click.option("--notes", "-n", default="", help="备注")
@click.option("--plan-id", help="计划 ID，默认使用最新创建的计划")
def split_plan(subject_name, tasks, priority, date_str, notes, plan_id):
    """拆分科目的学习计划，保存为可管理的计划项"""
    storage = Storage()

    if plan_id:
        plan = storage.get_plan(plan_id)
    else:
        plan = storage.get_active_plan()

    if not plan:
        click.echo("错误：未找到考试计划，请先创建计划")
        return

    from ..utils import get_subject_by_name_or_id_in_plan
    subject = get_subject_by_name_or_id_in_plan(storage, subject_name, plan.id)

    if not subject:
        subject = Subject(name=subject_name, plan_id=plan.id)
        subject = storage.save_subject(subject)
        plan.subjects.append(subject.id)
        storage.update_plan(plan)
        click.echo(f"✓ 已创建新科目: {subject_name}")

    priority_map = {'1': 1, 'high': 1, '2': 2, 'medium': 2, '3': 3, 'low': 3}
    priority_int = priority_map[priority]

    expected_date = None
    if date_str:
        parsed = parse_date(date_str)
        if not parsed:
            click.echo(f"错误：无效的日期格式 '{date_str}'")
            return
        expected_date = parsed.isoformat()

    if not tasks:
        click.echo("\n请使用 --tasks 指定要拆分的任务，例如:")
        click.echo(f"  studyplan plan split {subject.name} --tasks \"第一轮复习\" --tasks \"模拟练习\"")
        click.echo("\n也可以使用 plan item add 单独添加计划项:")
        click.echo(f"  studyplan plan item add {subject.name} \"第一轮复习\" --priority high")
        return

    saved_items = []
    for i, task_name in enumerate(tasks):
        item = PlanItem(
            title=task_name,
            subject_id=subject.id,
            subject_name=subject.name,
            plan_id=plan.id,
            priority=priority_int,
            expected_date=expected_date,
            notes=notes,
            order=i
        )
        item = storage.save_plan_item(item)
        saved_items.append(item)

    click.echo(f"\n✓ 已为科目 '{subject.name}' 添加 {len(saved_items)} 个计划项:")
    for i, item in enumerate(saved_items, 1):
        priority_str = get_priority_label(item.priority)
        date_str = item.expected_date or "未设置"
        click.echo(f"  {i}. [{item.id}] {item.title} (优先级: {priority_str}, 预计: {date_str}")
        if item.notes:
            click.echo(f"     备注: {item.notes}")

    click.echo(f"\n💡 使用 'studyplan plan item convert <item_id>' 可将计划项一键转为每日任务")
    click.echo(f"   使用 'studyplan plan show' 查看所有科目拆分计划")


@click.group("item")
def item():
    """管理科目拆分计划项（增删改查、一键转任务）"""
    pass


@item.command("add")
@click.argument("subject_name")
@click.argument("title")
@click.option("--priority", "-p", type=click.Choice(['1', '2', '3', 'high', 'medium', 'low']),
              default='2', help="优先级，默认中")
@click.option("--date", "-d", "date_str", help="预计完成日期")
@click.option("--notes", "-n", default="", help="备注")
@click.option("--order", "-o", type=int, default=0, help="排序序号")
@click.option("--plan-id", help="计划 ID，默认使用最新创建的计划")
def item_add(subject_name, title, priority, date_str, notes, order, plan_id):
    """添加单个计划项"""
    storage = Storage()

    if plan_id:
        plan = storage.get_plan(plan_id)
    else:
        plan = storage.get_active_plan()

    if not plan:
        click.echo("错误：未找到考试计划，请先创建计划")
        return

    from ..utils import get_subject_by_name_or_id_in_plan
    subject = get_subject_by_name_or_id_in_plan(storage, subject_name, plan.id)

    if not subject:
        click.echo(f"错误：在当前计划中未找到科目 '{subject_name}'")
        click.echo(f"请使用 --plan-id 指定其他计划，或先添加该科目到当前计划")
        return

    priority_map = {'1': 1, 'high': 1, '2': 2, 'medium': 2, '3': 3, 'low': 3}
    priority_int = priority_map[priority]

    expected_date = None
    if date_str:
        parsed = parse_date(date_str)
        if not parsed:
            click.echo(f"错误：无效的日期格式 '{date_str}'")
            return
        expected_date = parsed.isoformat()

    item = PlanItem(
        title=title,
        subject_id=subject.id,
        subject_name=subject.name,
        plan_id=plan.id,
        priority=priority_int,
        expected_date=expected_date,
        notes=notes,
        order=order
    )
    item = storage.save_plan_item(item)

    click.echo(f"✓ 已添加计划项: {title}")
    click.echo(f"  计划项 ID: {item.id}")
    click.echo(f"  科目: {subject.name}")
    click.echo(f"  优先级: {get_priority_label(priority_int)}")
    if expected_date:
        click.echo(f"  预计日期: {expected_date}")
    if notes:
        click.echo(f"  备注: {notes}")


@item.command("list")
@click.option("--subject", "-s", help="按科目筛选")
@click.option("--plan-id", help="按计划筛选，默认当前计划")
@click.option("--all", "-a", is_flag=True, help="显示所有计划的计划项")
def item_list(subject, plan_id, all):
    """列出计划项"""
    storage = Storage()

    if all:
        items = storage.get_all_plan_items()
    elif subject:
        from ..utils import get_subject_by_name_or_id
        subj = get_subject_by_name_or_id(storage, subject)
        if not subj:
            click.echo(f"错误：未找到科目 '{subject}'")
            return
        items = storage.get_plan_items_by_subject(subj.id)
    elif plan_id:
        plan = storage.get_plan(plan_id)
        if not plan:
            click.echo(f"错误：未找到计划 ID '{plan_id}'")
            return
        items = storage.get_plan_items_by_plan(plan.id)
    else:
        plan = storage.get_active_plan()
        if not plan:
            click.echo("尚未创建任何考试计划")
            return
        items = storage.get_plan_items_by_plan(plan.id)

    if not items:
        click.echo("暂无计划项")
        click.echo("使用 'studyplan plan item add <科目> <标题>' 添加")
        return

    click.echo(f"\n计划项列表 ({len(items)} 项):\n")

    status_map = {
        "pending": "待开始",
        "in_progress": "进行中",
        "completed": "已完成",
        "converted": "已转任务"
    }

    table_data = []
    for it in items:
        priority_str = get_priority_label(it.priority)
        status_str = status_map.get(it.status, it.status)
        date_str = it.expected_date or "-"
        table_data.append([
            it.id,
            it.subject_name,
            priority_str,
            it.title,
            status_str,
            date_str,
            it.notes or "-"
        ])

    click.echo(tabulate(
        table_data,
        headers=["ID", "科目", "优先级", "计划项", "状态", "预计日期", "备注"],
        tablefmt="simple"
    ))
    click.echo()


@item.command("show")
@click.argument("item_id")
def item_show(item_id):
    """显示计划项详情"""
    storage = Storage()
    item = storage.get_plan_item(item_id)

    if not item:
        click.echo(f"错误：未找到计划项 ID '{item_id}'")
        return

    status_map = {
        "pending": "待开始",
        "in_progress": "进行中",
        "completed": "已完成",
        "converted": "已转任务"
    }

    click.echo(f"\n{'='*50}")
    click.echo(f"📋 计划项详情")
    click.echo(f"{'='*50}")
    click.echo(f"  ID: {item.id}")
    click.echo(f"  标题: {item.title}")
    click.echo(f"  科目: {item.subject_name}")
    click.echo(f"  优先级: {get_priority_label(item.priority)}")
    click.echo(f"  状态: {status_map.get(item.status, item.status)}")
    if item.expected_date:
        click.echo(f"  预计日期: {item.expected_date}")
    if item.notes:
        click.echo(f"  备注: {item.notes}")
    if item.converted_task_id:
        click.echo(f"  已转为任务 ID: {item.converted_task_id}")
    click.echo(f"  排序序号: {item.order}")
    click.echo(f"  创建时间: {item.created_at}")
    click.echo()


@item.command("edit")
@click.argument("item_id")
@click.option("--title", "-t", help="修改标题")
@click.option("--priority", "-p", type=click.Choice(['1', '2', '3', 'high', 'medium', 'low']),
              help="修改优先级")
@click.option("--date", "-d", "date_str", help="修改预计日期")
@click.option("--notes", "-n", help="修改备注")
@click.option("--order", "-o", type=int, help="修改排序序号")
@click.option("--status", "-s",
              type=click.Choice(['pending', 'in_progress', 'completed']),
              help="修改状态")
def item_edit(item_id, title, priority, date_str, notes, order, status):
    """编辑计划项"""
    storage = Storage()
    item = storage.get_plan_item(item_id)

    if not item:
        click.echo(f"错误：未找到计划项 ID '{item_id}'")
        return

    if title:
        item.title = title

    if priority:
        priority_map = {'1': 1, 'high': 1, '2': 2, 'medium': 2, '3': 3, 'low': 3}
        item.priority = priority_map[priority]

    if date_str:
        parsed = parse_date(date_str)
        if not parsed:
            click.echo(f"错误：无效的日期格式 '{date_str}'")
            return
        item.expected_date = parsed.isoformat()

    if notes:
        item.notes = notes

    if order is not None:
        item.order = order

    if status:
        item.status = status

    storage.update_plan_item(item)
    click.echo(f"✓ 已更新计划项: {item.title}")


@item.command("remove")
@click.argument("item_id")
@click.option("--force", "-f", is_flag=True, help="不确认直接删除")
def item_remove(item_id, force):
    """删除计划项"""
    storage = Storage()
    item = storage.get_plan_item(item_id)

    if not item:
        click.echo(f"错误：未找到计划项 ID '{item_id}'")
        return

    if not force:
        confirm = click.confirm(f"确定要删除计划项 '{item.title}' 吗？")
        if not confirm:
            click.echo("已取消删除")
            return

    if storage.delete_plan_item(item_id):
        click.echo(f"✓ 已删除计划项: {item.title}")
    else:
        click.echo("错误：删除计划项失败")


@item.command("convert")
@click.argument("item_id")
@click.option("--date", "-d", "date_str", default="today", help="任务日期，默认今天")
@click.option("--keep", "-k", is_flag=True, help="保留计划项，不标记为已转换")
def item_convert(item_id, date_str, keep):
    """将计划项一键转为每日任务"""
    storage = Storage()
    item = storage.get_plan_item(item_id)

    if not item:
        click.echo(f"错误：未找到计划项 ID '{item_id}'")
        return

    if item.status == "converted" and not keep:
        click.echo(f"警告：该计划项已转为任务 (ID: {item.converted_task_id})")
        confirm = click.confirm("要再次转换吗？")
        if not confirm:
            return

    existing_task = None
    if not keep:
        all_tasks = storage.get_all_tasks()
        for t in all_tasks:
            if t.plan_item_id == item.id:
                existing_task = t
                break

    if existing_task and not keep:
        click.echo(f"警告：该计划项已有对应的任务 (ID: {existing_task.id})")
        confirm = click.confirm("确定要生成新的任务吗？")
        if not confirm:
            return

    parsed = parse_date(date_str)
    if not parsed:
        click.echo(f"错误：无效的日期格式 '{date_str}'")
        return

    task = Task(
        title=item.title,
        subject_id=item.subject_id,
        subject_name=item.subject_name,
        plan_item_id=item.id,
        priority=item.priority,
        due_date=parsed.isoformat(),
        description=item.notes
    )
    task = storage.save_task(task)

    if not keep:
        item.status = "converted"
        item.converted_task_id = task.id
        storage.update_plan_item(item)

    click.echo(f"✓ 已转为每日任务: {item.title}")
    click.echo(f"  任务 ID: {task.id}")
    click.echo(f"  科目: {item.subject_name}")
    click.echo(f"  优先级: {get_priority_label(item.priority)}")
    click.echo(f"  日期: {parsed.isoformat()}")
    if item.notes:
        click.echo(f"  描述: {item.notes}")
    click.echo(f"\n使用 'studyplan done mark {task.id} --duration <分钟>' 标记完成")


@item.command("schedule")
@click.option("--subject", "-s", "subject_name", help="指定科目名称，不指定则安排所有科目")
@click.option("--from", "-f", "from_date_str", default="tomorrow", help="开始日期，默认明天")
@click.option("--per-day", "-n", type=int, default=3, help="每天最多安排几个任务，默认 3")
@click.option("--priority-only", "-p", is_flag=True, help="只安排高优先级计划项")
@click.option("--plan-id", help="指定计划 ID，默认使用当前最新计划")
@click.option("--dry-run", is_flag=True, help="只预览不实际生成")
def item_schedule(subject_name, from_date_str, per_day, priority_only, plan_id, dry_run):
    """按科目批量安排待开始的计划项到未来几天"""
    storage = Storage()

    if plan_id:
        plan = storage.get_plan(plan_id)
    else:
        plan = storage.get_active_plan()

    if not plan:
        click.echo("错误：未找到考试计划，请先创建计划")
        return

    from ..utils import parse_date, get_subject_by_name_or_id_in_plan, get_priority_label

    from_date = parse_date(from_date_str)
    if not from_date:
        click.echo(f"错误：无效的日期格式 '{from_date_str}'")
        return

    if subject_name:
        subject = get_subject_by_name_or_id_in_plan(storage, subject_name, plan.id)
        if not subject:
            click.echo(f"错误：在当前计划中未找到科目 '{subject_name}'")
            return
        items = storage.get_plan_items_by_subject(subject.id)
    else:
        items = storage.get_plan_items_by_plan(plan.id)

    pending_items = [
        i for i in items
        if i.status in ["pending", "in_progress"]
        and (not priority_only or i.priority == 1)
    ]

    if not pending_items:
        click.echo("没有可安排的计划项")
        return

    existing_task_map = {}
    all_tasks = storage.get_all_tasks()
    for t in all_tasks:
        if t.plan_item_id:
            existing_task_map[t.plan_item_id] = t

    pending_items = [
        i for i in pending_items
        if i.id not in existing_task_map
    ]

    if not pending_items:
        click.echo("所有待安排的计划项都已有对应的任务")
        return

    pending_items.sort(key=lambda i: (i.priority, i.order, i.created_at))

    click.echo(f"计划: {plan.name}")
    click.echo(f"开始日期: {from_date.isoformat()}")
    click.echo(f"每天最多: {per_day} 个")
    if subject_name:
        click.echo(f"科目: {subject_name}")
    if priority_only:
        click.echo("仅安排高优先级")
    click.echo(f"待安排: {len(pending_items)} 个计划项")
    click.echo()

    schedule = {}
    current_date = from_date
    items_remaining = pending_items.copy()

    while items_remaining:
        day_items = items_remaining[:per_day]
        schedule[current_date.isoformat()] = day_items
        items_remaining = items_remaining[per_day:]
        current_date = current_date + timedelta(days=1)

    for date_str, day_items in schedule.items():
        click.echo(f"📅 {date_str}")
        for i, item in enumerate(day_items, 1):
            click.echo(f"  {i}. [{get_priority_label(item.priority)}] {item.title} ({item.subject_name})")
        click.echo()

    if dry_run:
        click.echo("(预览模式，未实际生成任务)")
        return

    confirm = click.confirm(f"确定要生成 {len(pending_items)} 个任务吗？")
    if not confirm:
        return

    total_created = 0
    for date_str, day_items in schedule.items():
        for item in day_items:
            task = Task(
                title=item.title,
                subject_id=item.subject_id,
                subject_name=item.subject_name,
                plan_item_id=item.id,
                priority=item.priority,
                due_date=date_str,
                description=item.notes
            )
            task = storage.save_task(task)

            item.status = "converted"
            item.converted_task_id = task.id
            storage.update_plan_item(item)

            total_created += 1

    click.echo(f"✓ 已生成 {total_created} 个任务，安排到 {len(schedule)} 天")
    click.echo(f"使用 'studyplan task list --date <日期>' 查看每日任务")


@plan.command("calendar")
@click.option("--days", "-n", type=int, default=14, help="显示未来 N 天，默认 14 天")
@click.option("--plan-id", "-p", help="指定计划 ID，默认使用当前最新计划")
@click.option("--all", "-a", "show_all", is_flag=True, help="显示所有计划的任务")
def plan_calendar(days, plan_id, show_all):
    """按日期查看近期学习安排"""
    storage = Storage()

    today = date.today()
    end_date = today + timedelta(days=days)

    if show_all:
        plan = None
        click.echo(f"📅 近期安排（所有计划，未来 {days} 天）")
    else:
        if plan_id:
            plan = storage.get_plan(plan_id)
        else:
            plan = storage.get_active_plan()

        if not plan:
            click.echo("错误：未找到考试计划，请先创建计划")
            return
        click.echo(f"📅 近期安排 - {plan.name}（未来 {days} 天）")

    all_tasks = storage.get_all_tasks()
    all_items = storage.get_all_plan_items()

    if plan and not show_all:
        all_tasks = [t for t in all_tasks if t.subject_id in [s.id for s in storage.get_subjects_by_plan(plan.id)]]
        all_items = [i for i in all_items if i.plan_id == plan.id]

    scheduled_tasks = {}
    for t in all_tasks:
        try:
            task_date = date.fromisoformat(t.due_date)
            if today <= task_date <= end_date:
                date_str = task_date.isoformat()
                if date_str not in scheduled_tasks:
                    scheduled_tasks[date_str] = []
                scheduled_tasks[date_str].append(t)
        except (ValueError, TypeError):
            continue

    unscheduled_high_priority = [
        i for i in all_items
        if i.status in ["pending", "in_progress"]
        and i.priority == 1
        and not any(t.plan_item_id == i.id for t in all_tasks)
    ]

    from ..utils import get_priority_label

    click.echo(f"{'='*60}")
    click.echo(f"  今天: {today.isoformat()}")
    click.echo(f"{'='*60}")

    current = today
    has_content = False
    while current <= end_date:
        date_str = current.isoformat()
        tasks = scheduled_tasks.get(date_str, [])
        is_today = current == today
        weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][current.weekday()]

        if tasks or is_today:
            has_content = True
            today_marker = " 📍" if is_today else ""
            click.echo(f"\n📆 {date_str} ({weekday}){today_marker}")

            if tasks:
                tasks.sort(key=lambda t: (t.priority, t.due_date))
                for i, t in enumerate(tasks, 1):
                    status_icon = "✅" if t.status == "done" else "⏳" if t.status == "postponed" else "📋"
                    subject_str = f" [{t.subject_name}]" if t.subject_name else ""
                    priority_str = f" [{get_priority_label(t.priority)}]" if t.priority != 2 else ""
                    plan_item_str = f" (来自计划)" if t.plan_item_id else ""
                    click.echo(f"  {status_icon} {i}. {t.title}{subject_str}{priority_str}{plan_item_str}")
            else:
                click.echo(f"  (暂无安排)")

        current = current + timedelta(days=1)

    if not has_content:
        click.echo(f"\n  未来 {days} 天暂无安排")

    if unscheduled_high_priority:
        click.echo(f"\n{'='*60}")
        click.echo(f"⚠️  未安排日期的高优先级计划项 ({len(unscheduled_high_priority)} 个):")
        click.echo(f"{'='*60}")
        unscheduled_high_priority.sort(key=lambda i: (i.priority, i.order, i.created_at))
        for i, item in enumerate(unscheduled_high_priority, 1):
            exp_date = f" (预计: {item.expected_date})" if item.expected_date else ""
            click.echo(f"  {i}. [{get_priority_label(item.priority)}] {item.title} ({item.subject_name}){exp_date}")
        click.echo(f"\n使用 'studyplan plan item schedule --priority-only' 快速安排这些计划项")

    click.echo()
    click.echo("使用 'studyplan plan item schedule' 批量安排更多计划项")
    click.echo("使用 'studyplan task list --date <日期>' 查看某日详细任务")
    click.echo()


plan.add_command(item)
