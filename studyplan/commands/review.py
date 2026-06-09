"""review 命令组 - 错题复习管理"""
import click
from tabulate import tabulate
from datetime import date, timedelta

from ..storage import Storage
from ..models import ReviewItem
from ..utils import parse_date, get_subject_by_name_or_id, format_duration


@click.group()
def review():
    """管理错题和复习内容"""
    pass


@review.command("add")
@click.argument("content")
@click.option("--subject", "-s", help="关联科目名称或 ID")
@click.option("--source", "-o", default="", help="题目来源（如习题集P12、模拟卷一）")
@click.option("--notes", "-n", default="", help="笔记和解题思路")
@click.option("--mastery", "-m", type=click.IntRange(0, 100), default=0,
              help="掌握程度 0-100，默认 0")
def add_review(content, subject, source, notes, mastery):
    """添加错题或需要复习的内容"""
    storage = Storage()

    subject_id = None
    subject_name = ""
    if subject:
        active_plan = storage.get_active_plan()
        plan_id = active_plan.id if active_plan else None
        subj = get_subject_by_name_or_id(storage, subject, plan_id)
        if subj:
            subject_id = subj.id
            subject_name = subj.name
        else:
            click.echo(f"警告：未找到科目 '{subject}'")

    review = ReviewItem(
        content=content,
        subject_id=subject_id,
        subject_name=subject_name,
        source=source,
        mastery=mastery,
        notes=notes,
        next_review=date.today().isoformat()
    )
    review = storage.save_review(review)

    click.echo(f"✓ 已添加复习项: {content[:50]}{'...' if len(content) > 50 else ''}")
    click.echo(f"  复习项 ID: {review.id}")
    if subject_name:
        click.echo(f"  科目: {subject_name}")
    if source:
        click.echo(f"  来源: {source}")
    click.echo(f"  下次复习: {review.next_review}")


@review.command("schedule")
@click.argument("review_id")
@click.option("--date", "-d", "date_str", default="today", help="下次复习日期")
@click.option("--days", "-D", type=int, help="N 天后复习")
@click.option("--mastery", "-m", type=click.IntRange(0, 100),
              help="更新掌握程度 0-100")
def schedule_review(review_id, date_str, days, mastery):
    """安排复习时间，更新掌握程度"""
    storage = Storage()
    review = storage.get_review(review_id)

    if not review:
        click.echo(f"错误：未找到复习项 ID '{review_id}'")
        return

    if days:
        next_date = date.today() + timedelta(days=days)
    else:
        next_date = parse_date(date_str)
        if not next_date:
            click.echo(f"错误：无效的日期格式 '{date_str}'")
            return

    review.next_review = next_date.isoformat()
    review.last_reviewed = date.today().isoformat()
    review.review_count += 1

    if mastery is not None:
        review.mastery = mastery

    storage.update_review(review)

    click.echo(f"✓ 已安排复习: {review.content[:50]}{'...' if len(review.content) > 50 else ''}")
    click.echo(f"  下次复习: {review.next_review}")
    click.echo(f"  复习次数: {review.review_count}")
    click.echo(f"  掌握程度: {review.mastery}%")


@review.command("list")
@click.option("--due", "-d", is_flag=True, help="只显示到期需要复习的")
@click.option("--subject", "-s", help="按科目筛选")
@click.option("--all", "-a", is_flag=True, help="显示所有复习项")
@click.option("--sort-by-mastery", "sort_mastery", is_flag=True, help="按掌握程度排序")
def list_reviews(due, subject, all, sort_mastery):
    """列出复习项（默认显示今日需要复习的）"""
    storage = Storage()

    if all:
        reviews = storage.get_all_reviews()
    elif due:
        reviews = storage.get_reviews_due()
    else:
        reviews = storage.get_reviews_due()

    if subject:
        active_plan = storage.get_active_plan()
        plan_id = active_plan.id if active_plan else None
        subj = get_subject_by_name_or_id(storage, subject, plan_id)
        if subj:
            reviews = [r for r in reviews if r.subject_id == subj.id]
        else:
            click.echo(f"警告：未找到科目 '{subject}'")

    if sort_mastery:
        reviews = sorted(reviews, key=lambda r: r.mastery)
    else:
        reviews = sorted(reviews, key=lambda r: r.next_review)

    if not reviews:
        if due or not all:
            click.echo("🎉 今天没有需要复习的内容！")
        else:
            click.echo("暂无复习项")
            click.echo("使用 'studyplan review add <内容>' 添加复习项")
        return

    title = "今日待复习" if (due or not all) else "所有复习项"
    click.echo(f"\n{'='*70}")
    click.echo(f"📖 {title} ({len(reviews)} 项)")
    click.echo(f"{'='*70}")

    table_data = []
    for r in reviews:
        mastery_color = "red" if r.mastery < 40 else "yellow" if r.mastery < 70 else "green"
        is_overdue = r.next_review < date.today().isoformat()
        overdue_tag = " [逾期]" if is_overdue else ""

        table_data.append([
            r.id,
            r.subject_name or "-",
            r.content[:40] + ("..." if len(r.content) > 40 else ""),
            r.source or "-",
            click.style(f"{r.mastery}%", fg=mastery_color),
            r.review_count,
            r.next_review + overdue_tag
        ])

    click.echo(tabulate(
        table_data,
        headers=["ID", "科目", "内容", "来源", "掌握度", "复习次数", "下次复习"],
        tablefmt="simple"
    ))
    click.echo()


@review.command("show")
@click.argument("review_id")
def show_review(review_id):
    """显示复习项详情"""
    storage = Storage()
    review = storage.get_review(review_id)

    if not review:
        click.echo(f"错误：未找到复习项 ID '{review_id}'")
        return

    click.echo(f"\n{'='*60}")
    click.echo(f"📖 复习项详情")
    click.echo(f"{'='*60}")
    click.echo(f"  ID: {review.id}")
    click.echo(f"  科目: {review.subject_name or '未设置'}")
    if review.source:
        click.echo(f"  来源: {review.source}")
    click.echo(f"\n  内容:")
    click.echo(f"    {review.content}")
    if review.notes:
        click.echo(f"\n  笔记:")
        click.echo(f"    {review.notes}")
    click.echo(f"\n  掌握程度: {review.mastery}%")
    click.echo(f"  复习次数: {review.review_count}")
    if review.last_reviewed:
        click.echo(f"  上次复习: {review.last_reviewed}")
    click.echo(f"  下次复习: {review.next_review}")
    click.echo(f"  创建时间: {review.created_at}")
    click.echo()


@review.command("done")
@click.argument("review_id")
@click.option("--mastery", "-m", type=click.IntRange(0, 100), default=None,
              help="更新掌握程度 0-100，保持原程度则不指定")
@click.option("--interval", "-i", type=int,
              help="自定义下次复习间隔天数，默认根据掌握程度自动计算")
def complete_review(review_id, mastery, interval):
    """完成一次复习，自动安排下次复习时间"""
    storage = Storage()
    review = storage.get_review(review_id)

    if not review:
        click.echo(f"错误：未找到复习项 ID '{review_id}'")
        return

    if mastery is not None:
        review.mastery = mastery

    if interval:
        days = interval
    else:
        mastery_level = review.mastery
        if mastery_level >= 90:
            days = 14
        elif mastery_level >= 70:
            days = 7
        elif mastery_level >= 50:
            days = 3
        elif mastery_level >= 30:
            days = 2
        else:
            days = 1

    review.last_reviewed = date.today().isoformat()
    review.next_review = (date.today() + timedelta(days=days)).isoformat()
    review.review_count += 1

    storage.update_review(review)

    click.echo(f"✓ 已完成复习: {review.content[:50]}{'...' if len(review.content) > 50 else ''}")
    click.echo(f"  掌握程度: {review.mastery}%")
    click.echo(f"  复习次数: {review.review_count}")
    click.echo(f"  下次复习: {review.next_review} ({days} 天后)")


@review.command("edit")
@click.argument("review_id")
@click.option("--content", "-c", help="修改复习内容")
@click.option("--subject", "-s", help="修改关联科目")
@click.option("--source", "-o", help="修改来源")
@click.option("--notes", "-n", help="修改笔记")
@click.option("--mastery", "-m", type=click.IntRange(0, 100), help="修改掌握程度")
def edit_review(review_id, content, subject, source, notes, mastery):
    """编辑复习项"""
    storage = Storage()
    review = storage.get_review(review_id)

    if not review:
        click.echo(f"错误：未找到复习项 ID '{review_id}'")
        return

    if content:
        review.content = content

    if subject:
        if subject.lower() == "none":
            review.subject_id = None
            review.subject_name = ""
        else:
            active_plan = storage.get_active_plan()
            plan_id = active_plan.id if active_plan else None
            subj = get_subject_by_name_or_id(storage, subject, plan_id)
            if subj:
                review.subject_id = subj.id
                review.subject_name = subj.name
            else:
                click.echo(f"警告：未找到科目 '{subject}'")

    if source:
        review.source = source

    if notes:
        review.notes = notes

    if mastery is not None:
        review.mastery = mastery

    storage.update_review(review)
    click.echo(f"✓ 已更新复习项")


@review.command("remove")
@click.argument("review_id")
@click.option("--force", "-f", is_flag=True, help="不确认直接删除")
def remove_review(review_id, force):
    """删除复习项"""
    storage = Storage()
    review = storage.get_review(review_id)

    if not review:
        click.echo(f"错误：未找到复习项 ID '{review_id}'")
        return

    if not force:
        confirm = click.confirm(f"确定要删除此复习项吗？\n内容: {review.content[:60]}...")
        if not confirm:
            click.echo("已取消删除")
            return

    if storage.delete_review(review_id):
        click.echo(f"✓ 已删除复习项")
    else:
        click.echo("错误：删除复习项失败")


@review.command("today")
def today_review():
    """查看今日复习清单"""
    storage = Storage()
    today = date.today().isoformat()

    reviews = storage.get_reviews_due(today)
    reviews = sorted(reviews, key=lambda r: (r.mastery, r.next_review))

    if not reviews:
        click.echo("\n🎉 今天没有需要复习的内容！继续保持！\n")
        return

    click.echo(f"\n{'='*60}")
    click.echo(f"📖 今日复习清单 - {today}")
    click.echo(f"{'='*60}")

    need_work = [r for r in reviews if r.mastery < 50]
    progressing = [r for r in reviews if 50 <= r.mastery < 80]
    mastered = [r for r in reviews if r.mastery >= 80]

    def print_group(title, items, icon):
        if items:
            click.echo(f"\n{icon} {title} ({len(items)}):")
            for i, r in enumerate(items, 1):
                subject_tag = f" ({r.subject_name})" if r.subject_name else ""
                content_preview = r.content[:30] + ("..." if len(r.content) > 30 else "")
                click.echo(f"  {i}. [{r.id}] {content_preview}{subject_tag} - {r.mastery}%")

    print_group("需要重点复习", need_work, "🔴")
    print_group("持续巩固", progressing, "🟡")
    print_group("已掌握", mastered, "🟢")

    total_study_time = len(reviews) * 15
    click.echo(f"\n⏱ 预计复习时间: 约 {format_duration(total_study_time)} (按每项15分钟估算)")
    click.echo()
