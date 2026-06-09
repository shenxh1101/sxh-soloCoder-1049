"""stats 命令组 - 学习统计"""
import click
from tabulate import tabulate
from datetime import date, timedelta
from collections import defaultdict

from ..storage import Storage
from ..utils import format_duration, get_week_range, format_date


@click.group()
def stats():
    """查看学习统计数据"""
    pass


@stats.command("streak")
def show_streak():
    """查看连续学习天数"""
    storage = Storage()
    streak = storage.get_streak()
    study_dates = storage.get_study_dates()

    click.echo(f"\n{'='*50}")
    click.echo(f"🔥 连续学习天数")
    click.echo(f"{'='*50}")

    if streak == 0:
        click.echo("\n  暂无连续学习记录")
        click.echo("  完成一个任务并记录学习时长，开始你的连续学习吧！")
    else:
        emoji = "💪" if streak >= 30 else "🔥" if streak >= 7 else "✨"
        click.echo(f"\n  {emoji} 连续学习: {streak} 天")

        if streak >= 365:
            click.echo("  太厉害了！坚持了一整年！")
        elif streak >= 100:
            click.echo("  百日坚持，令人敬佩！")
        elif streak >= 30:
            click.echo("  月度目标达成！继续保持！")
        elif streak >= 7:
            click.echo("  周目标达成！加油！")
        elif streak >= 3:
            click.echo("  好的开始，继续坚持！")

    if study_dates:
        click.echo(f"\n  累计学习天数: {len(study_dates)} 天")
        first_date = study_dates[0]
        click.echo(f"  首次学习日期: {first_date}")

    click.echo()


@stats.command("subject")
@click.option("--days", "-d", type=int, default=7, help="统计最近 N 天，默认 7 天")
@click.option("--all", "-a", is_flag=True, help="统计所有历史数据")
def subject_stats(days, all):
    """按科目统计学习投入时间"""
    storage = Storage()

    if all:
        records = storage.get_all_records()
        period = "全部历史"
    else:
        start_date = (date.today() - timedelta(days=days - 1)).isoformat()
        end_date = date.today().isoformat()
        records = storage.get_records_by_date_range(start_date, end_date)
        period = f"最近 {days} 天"

    if not records:
        click.echo(f"\n{period} 暂无学习记录\n")
        return

    subject_stats = defaultdict(lambda: {"duration": 0, "count": 0})
    for r in records:
        key = r.subject_name or "未分类"
        subject_stats[key]["duration"] += r.duration
        subject_stats[key]["count"] += 1

    total_duration = sum(s["duration"] for s in subject_stats.values())
    total_count = sum(s["count"] for s in subject_stats.values())

    click.echo(f"\n{'='*60}")
    click.echo(f"📊 科目学习统计 - {period}")
    click.echo(f"{'='*60}")

    sorted_subjects = sorted(subject_stats.items(), key=lambda x: x[1]["duration"], reverse=True)

    table_data = []
    for i, (subject, data) in enumerate(sorted_subjects, 1):
        duration = data["duration"]
        count = data["count"]
        percentage = (duration / total_duration * 100) if total_duration > 0 else 0

        bar_length = 20
        filled = int(bar_length * percentage / 100)
        bar = "█" * filled + "░" * (bar_length - filled)

        table_data.append([
            i,
            subject,
            format_duration(duration),
            f"{count} 次",
            f"{percentage:.1f}%",
            bar
        ])

    click.echo(tabulate(
        table_data,
        headers=["排名", "科目", "总时长", "次数", "占比", "分布"],
        tablefmt="simple",
        colalign=["right", "left", "right", "right", "right", "left"]
    ))

    click.echo(f"\n📈 总计: {format_duration(total_duration)} / {total_count} 次学习记录")
    click.echo()


@stats.command("daily")
@click.option("--days", "-d", type=int, default=7, help="显示最近 N 天，默认 7 天")
def daily_stats(days):
    """查看每日学习时长统计"""
    storage = Storage()

    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)

    records = storage.get_records_by_date_range(start_date.isoformat(), end_date.isoformat())

    if not records:
        click.echo(f"\n最近 {days} 天暂无学习记录\n")
        return

    daily_stats = defaultdict(int)
    for r in records:
        daily_stats[r.date] += r.duration

    click.echo(f"\n{'='*60}")
    click.echo(f"📅 每日学习时长统计 - 最近 {days} 天")
    click.echo(f"{'='*60}\n")

    max_duration = max(daily_stats.values()) if daily_stats else 1
    total_duration = sum(daily_stats.values())
    days_with_study = len(daily_stats)

    for i in range(days):
        current_date = start_date + timedelta(days=i)
        date_str = current_date.isoformat()
        duration = daily_stats.get(date_str, 0)

        if max_duration > 0:
            bar_length = 30
            filled = int(bar_length * duration / max_duration)
            bar = "█" * filled + "░" * (bar_length - filled)
        else:
            bar = "░" * 30

        weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][current_date.weekday()]
        is_today = current_date == end_date
        today_marker = " 今天" if is_today else ""

        duration_str = format_duration(duration) if duration > 0 else "-"
        click.echo(f"  {date_str} ({weekday}){today_marker} |{bar}| {duration_str}")

    avg_duration = total_duration / days if days > 0 else 0
    click.echo(f"\n📊 总计: {format_duration(total_duration)} / 日均: {format_duration(int(avg_duration))}")
    click.echo(f"   有 {days_with_study}/{days} 天进行了学习")
    click.echo()


@stats.command("weekly")
@click.option("--week", "-w", type=int, help="指定周数（1-52），默认本周")
@click.option("--year", "-y", type=int, help="指定年份，默认今年")
def weekly_stats(week, year):
    """查看周学习统计"""
    storage = Storage()

    ref_date = date.today()
    if year:
        ref_date = ref_date.replace(year=year)
    if week:
        try:
            ref_date = date.fromisocalendar(year or ref_date.year, week, 1)
        except ValueError:
            click.echo(f"错误：无效的周数 {week}")
            return

    start_date, end_date = get_week_range(ref_date)
    records = storage.get_records_by_date_range(start_date.isoformat(), end_date.isoformat())

    week_num = ref_date.isocalendar()[1]
    year_num = ref_date.year

    click.echo(f"\n{'='*60}")
    click.echo(f"📊 {year_num}年 第{week_num}周 学习统计")
    click.echo(f"  {start_date.isoformat()} - {end_date.isoformat()}")
    click.echo(f"{'='*60}\n")

    if not records:
        click.echo("  本周暂无学习记录\n")
        return

    daily = defaultdict(int)
    subjects = defaultdict(int)
    total_duration = 0

    for r in records:
        daily[r.date] += r.duration
        subjects[r.subject_name or "未分类"] += r.duration
        total_duration += r.duration

    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    for i in range(7):
        current = start_date + timedelta(days=i)
        date_str = current.isoformat()
        dur = daily.get(date_str, 0)
        marker = " ✅" if dur > 0 else ""
        click.echo(f"  {weekdays[i]} {date_str}: {format_duration(dur) if dur > 0 else '-'}{marker}")

    click.echo(f"\n📈 本周总学习时长: {format_duration(total_duration)}")

    if subjects:
        click.echo(f"\n📚 科目分布:")
        sorted_subj = sorted(subjects.items(), key=lambda x: x[1], reverse=True)
        for subj, dur in sorted_subj:
            pct = dur / total_duration * 100 if total_duration > 0 else 0
            click.echo(f"  {subj}: {format_duration(dur)} ({pct:.1f}%)")

    avg_daily = total_duration / 7
    click.echo(f"\n📊 日均学习: {format_duration(int(avg_daily))}")
    days_studied = sum(1 for d in daily.values() if d > 0)
    click.echo(f"   学习天数: {days_studied}/7 天")
    click.echo()


@stats.command("export")
@click.option("--week", "-w", type=int, help="指定周数（1-52），默认本周")
@click.option("--year", "-y", type=int, help="指定年份，默认今年")
@click.option("--output", "-o", default=None, help="输出文件路径，默认打印到终端")
def export_weekly(week, year, output):
    """导出周报文本"""
    storage = Storage()

    ref_date = date.today()
    if year:
        ref_date = ref_date.replace(year=year)
    if week:
        try:
            ref_date = date.fromisocalendar(year or ref_date.year, week, 1)
        except ValueError:
            click.echo(f"错误：无效的周数 {week}")
            return

    start_date, end_date = get_week_range(ref_date)
    records = storage.get_records_by_date_range(start_date.isoformat(), end_date.isoformat())
    tasks = storage.get_all_tasks()

    week_num = ref_date.isocalendar()[1]
    year_num = ref_date.year

    week_tasks = [t for t in tasks if start_date.isoformat() <= t.due_date <= end_date.isoformat()]
    done_tasks = [t for t in week_tasks if t.status == "done"]

    daily = defaultdict(int)
    subjects = defaultdict(int)
    total_duration = 0

    for r in records:
        daily[r.date] += r.duration
        subjects[r.subject_name or "未分类"] += r.duration
        total_duration += r.duration

    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    report_lines = []
    report_lines.append("=" * 60)
    report_lines.append(f"📊 学习周报 - {year_num}年第{week_num}周")
    report_lines.append(f"   {start_date.isoformat()} - {end_date.isoformat()}")
    report_lines.append("=" * 60)
    report_lines.append("")

    report_lines.append("一、本周学习概况")
    report_lines.append("-" * 30)
    report_lines.append(f"  总学习时长: {format_duration(total_duration)}")
    avg_daily = total_duration / 7
    report_lines.append(f"  日均学习: {format_duration(int(avg_daily))}")
    days_studied = sum(1 for d in daily.values() if d > 0)
    report_lines.append(f"  学习天数: {days_studied}/7 天")
    completion_rate = (len(done_tasks) / len(week_tasks) * 100) if week_tasks else 0
    report_lines.append(f"  任务完成率: {len(done_tasks)}/{len(week_tasks)} ({completion_rate:.1f}%)")
    report_lines.append("")

    report_lines.append("二、每日学习记录")
    report_lines.append("-" * 30)
    for i in range(7):
        current = start_date + timedelta(days=i)
        date_str = current.isoformat()
        dur = daily.get(date_str, 0)
        status = "✓" if dur > 0 else "✗"
        report_lines.append(f"  {status} {weekdays[i]} {date_str}: {format_duration(dur) if dur > 0 else '-'}")
    report_lines.append("")

    if subjects:
        report_lines.append("三、科目时间分布")
        report_lines.append("-" * 30)
        sorted_subj = sorted(subjects.items(), key=lambda x: x[1], reverse=True)
        for subj, dur in sorted_subj:
            pct = dur / total_duration * 100 if total_duration > 0 else 0
            report_lines.append(f"  {subj}: {format_duration(dur)} ({pct:.1f}%)")
        report_lines.append("")

    if done_tasks:
        report_lines.append("四、本周完成的任务")
        report_lines.append("-" * 30)
        sorted_done = sorted(done_tasks, key=lambda t: t.completed_at or "")
        for t in sorted_done:
            subject_tag = f" [{t.subject_name}]" if t.subject_name else ""
            dur_tag = f" ({format_duration(t.study_duration)})" if t.study_duration > 0 else ""
            report_lines.append(f"  ✓ {t.title}{subject_tag}{dur_tag}")
        report_lines.append("")

    pending_tasks = [t for t in week_tasks if t.status != "done"]
    if pending_tasks:
        report_lines.append("五、本周未完成的任务")
        report_lines.append("-" * 30)
        for t in pending_tasks:
            subject_tag = f" [{t.subject_name}]" if t.subject_name else ""
            report_lines.append(f"  ☐ {t.title}{subject_tag}")
        report_lines.append("")

    streak = storage.get_streak()
    if streak > 0:
        report_lines.append(f"🔥 连续学习: {streak} 天")
        report_lines.append("")

    report_lines.append("=" * 60)
    report_lines.append("下周继续加油！💪")
    report_lines.append("=" * 60)

    report_text = "\n".join(report_lines)

    if output:
        try:
            with open(output, 'w', encoding='utf-8') as f:
                f.write(report_text)
            click.echo(f"✓ 周报已导出到: {output}")
        except IOError as e:
            click.echo(f"错误：导出失败 - {e}")
            click.echo("\n" + report_text)
    else:
        click.echo("\n" + report_text)


@stats.command("overview")
def overview():
    """查看学习总览"""
    storage = Storage()

    all_records = storage.get_all_records()
    all_tasks = storage.get_all_tasks()
    streak = storage.get_streak()
    study_dates = storage.get_study_dates()

    done_tasks = [t for t in all_tasks if t.status == "done"]
    pending_tasks = [t for t in all_tasks if t.status == "pending"]

    total_duration = sum(r.duration for r in all_records)

    subject_stats = defaultdict(int)
    for r in all_records:
        subject_stats[r.subject_name or "未分类"] += r.duration

    click.echo(f"\n{'='*60}")
    click.echo(f"📊 学习总览")
    click.echo(f"{'='*60}\n")

    click.echo(f"  🔥 连续学习: {streak} 天")
    click.echo(f"  📅 累计学习: {len(study_dates)} 天")
    click.echo(f"  ⏱ 总学习时长: {format_duration(total_duration)}")
    click.echo(f"  ✅ 已完成任务: {len(done_tasks)} 个")
    click.echo(f"  ⏳ 待完成任务: {len(pending_tasks)} 个")

    if study_dates:
        avg_per_day = total_duration / len(study_dates) if len(study_dates) > 0 else 0
        click.echo(f"  📈 平均每天: {format_duration(int(avg_per_day))}")

    if subject_stats:
        click.echo(f"\n📚 学习科目:")
        sorted_subj = sorted(subject_stats.items(), key=lambda x: x[1], reverse=True)
        for subj, dur in sorted_subj:
            pct = dur / total_duration * 100 if total_duration > 0 else 0
            click.echo(f"     {subj}: {format_duration(dur)} ({pct:.1f}%)")

    click.echo()
