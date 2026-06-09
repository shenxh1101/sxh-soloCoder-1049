"""学习计划命令行工具主入口"""
import click
from datetime import date

from . import __version__
from .commands.plan import plan
from .commands.task import task
from .commands.done import done
from .commands.review import review
from .commands.stats import stats
from .storage import Storage
from .utils import calculate_days_remaining, format_duration


@click.group(help="📚 学习计划命令行工具 - 备考用户的每日学习任务管理")
@click.version_option(__version__, "-v", "--version", message="studyplan %(version)s")
def cli():
    pass


@cli.command("today", help="快速查看今日概览（任务 + 复习）")
def today_overview():
    """快速查看今日概览"""
    storage = Storage()
    today = date.today().isoformat()

    click.echo(f"\n{'='*70}")
    click.echo(f"📅 今日学习概览 - {today}")
    click.echo(f"{'='*70}")

    plan = storage.get_active_plan()
    if plan and plan.exam_date:
        days = calculate_days_remaining(plan.exam_date)
        if days is not None and days > 0:
            click.echo(f"\n🎯 考试目标: {plan.name} (剩余 {days} 天)")
        elif days == 0:
            click.echo(f"\n🎯 考试目标: {plan.name} (考试就在今天！)")

    streak = storage.get_streak()
    if streak > 0:
        click.echo(f"🔥 连续学习: {streak} 天")

    tasks_dict = {}
    for t in storage.get_tasks_by_date(today):
        tasks_dict[t.id] = t
    for t in storage.get_all_tasks():
        if t.status == "postponed" and t.due_date <= today:
            if t.id not in tasks_dict:
                tasks_dict[t.id] = t
    all_tasks = [*tasks_dict.values()]

    done_count = sum(1 for t in all_tasks if t.status == "done")
    pending_count = sum(1 for t in all_tasks if t.status == "pending")
    postponed_count = sum(1 for t in all_tasks if t.status == "postponed")

    records = storage.get_records_by_date(today)
    total_duration = sum(r.duration for r in records)

    click.echo(f"\n📋 任务: ✅{done_count} ⏳{pending_count} ⏰{postponed_count}")
    if total_duration > 0:
        click.echo(f"⏱ 已学习: {format_duration(total_duration)}")

    if pending_count + postponed_count > 0:
        click.echo(f"\n待完成任务 Top 5:")
        pending_tasks = [t for t in all_tasks if t.status != "done"]
        pending_tasks = sorted(pending_tasks, key=lambda t: t.priority)[:5]
        for t in pending_tasks:
            priority_tag = "🔴" if t.priority == 1 else "🟡" if t.priority == 2 else "🟢"
            subject_tag = f" ({t.subject_name})" if t.subject_name else ""
            status_tag = " [推迟]" if t.status == "postponed" else ""
            click.echo(f"  {priority_tag} [{t.id}] {t.title}{subject_tag}{status_tag}")

    reviews = storage.get_reviews_due(today)
    if reviews:
        need_work = [r for r in reviews if r.mastery < 50]
        click.echo(f"\n📖 复习: {len(reviews)} 项待复习"
                   + (f" (重点 {len(need_work)} 项)" if need_work else ""))
        if need_work:
            for r in need_work[:3]:
                subject_tag = f" ({r.subject_name})" if r.subject_name else ""
                content = r.content[:25] + ("..." if len(r.content) > 25 else "")
                click.echo(f"  🔴 [{r.id}] {content}{subject_tag}")

    click.echo("\n💡 快捷命令:")
    click.echo("  studyplan task today    - 查看今日任务清单")
    click.echo("  studyplan review today  - 查看今日复习清单")
    click.echo("  studyplan done summary  - 查看今日学习总结")
    click.echo("  studyplan task add <任务> - 添加新任务")
    click.echo()


@cli.command("init", help="初始化学习计划（交互式创建考试目标）")
def init_wizard():
    """交互式初始化学习计划"""
    click.echo("\n" + "="*50)
    click.echo("🚀 学习计划初始化向导")
    click.echo("="*50 + "\n")

    storage = Storage()
    existing_plans = storage.get_all_plans()

    if existing_plans:
        click.echo(f"检测到已存在 {len(existing_plans)} 个考试计划")
        if not click.confirm("要创建新的考试计划吗？"):
            click.echo("已取消。\n")
            return

    click.echo("\n📝 让我们来创建你的考试目标吧！\n")

    name = click.prompt("请输入考试名称（如：考研、公务员考试、CPA）", type=str)

    exam_date_str = click.prompt(
        "请输入考试日期（YYYY-MM-DD），可直接按 Enter 跳过",
        default="",
        show_default=False
    )

    exam_date = None
    if exam_date_str:
        from .utils import parse_date
        parsed = parse_date(exam_date_str)
        if parsed:
            exam_date = parsed.isoformat()
        else:
            click.echo("⚠ 日期格式不正确，已跳过考试日期设置")

    subjects_input = click.prompt(
        "请输入考试科目，多个科目用逗号分隔（如：数学,英语,政治）",
        default="",
        show_default=False
    )

    from .models import ExamPlan, Subject

    plan = ExamPlan(name=name, exam_date=exam_date)
    plan = storage.save_plan(plan)

    subject_list = []
    if subjects_input:
        subjects = [s.strip() for s in subjects_input.split(",") if s.strip()]
        for subj_name in subjects:
            subject = Subject(name=subj_name, plan_id=plan.id)
            subject = storage.save_subject(subject)
            subject_list.append(subject)

    plan.subjects = [s.id for s in subject_list]
    storage.update_plan(plan)

    click.echo("\n" + "="*50)
    click.echo("✅ 学习计划创建成功！")
    click.echo("="*50)
    click.echo(f"\n📚 考试名称: {name}")
    if exam_date:
        days = calculate_days_remaining(exam_date)
        if days and days > 0:
            click.echo(f"📅 考试日期: {exam_date} (剩余 {days} 天)")
        else:
            click.echo(f"📅 考试日期: {exam_date}")
    if subject_list:
        click.echo(f"📖 考试科目: {', '.join(s.name for s in subject_list)}")
    click.echo(f"🆔 计划 ID: {plan.id}")

    click.echo("\n🎯 下一步建议:")
    click.echo(f"  1. 添加每日任务: studyplan task add --subject {subject_list[0].name if subject_list else '<科目>'} '<任务名称>'")
    click.echo(f"  2. 查看今日清单: studyplan task today")
    click.echo(f"  3. 标记任务完成: studyplan done mark <任务ID> --duration 60")
    click.echo(f"  4. 添加错题复习: studyplan review add '<错题内容>' --subject <科目>")
    click.echo()


cli.add_command(plan)
cli.add_command(task)
cli.add_command(done)
cli.add_command(review)
cli.add_command(stats)


if __name__ == "__main__":
    cli()
