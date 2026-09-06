import calendar
from datetime import date, datetime, timedelta
from typing import Optional, List
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.database import get_db
from backend.app.models import ExamRecord, ExamScore, Subject, MistakeRecord, HomeworkItem
from backend.app.routers.paper import CORE_7_SUBJECTS
from backend.app.schemas import (
    ExamCreateIn,
    ExamUpdateIn,
    ExamListItemOut,
    ExamDetailOut,
    ExamScoreOut,
    ExamTrendsOut,
    ExamTrendsItemOut,
    ExamRadarOut,
    RadarIndicatorOut,
    SubjectWeaknessItemOut,
    MonthlyAnalyticsOut,
    DailyCompletionItemOut,
    SubjectMissingCountOut,
)

router = APIRouter(prefix="/api/exams", tags=["成绩台账与学情分析"])
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


def _calc_rate(score: Optional[float], full_score: Optional[float]) -> Optional[float]:
    if score is None or full_score is None or full_score <= 0:
        return None
    return round((score / full_score) * 100, 1)


def _format_exam_scores_out(scores: List[ExamScore]) -> List[ExamScoreOut]:
    result = []
    for s in scores:
        sub_name = s.subject.name if s.subject else f"科目{s.subject_id}"
        rate = _calc_rate(s.score, s.full_score) if not s.is_absent else None
        result.append(
            ExamScoreOut(
                id=s.id,
                subject_id=s.subject_id,
                subject_name=sub_name,
                score=s.score if not s.is_absent else None,
                full_score=s.full_score,
                rate=rate,
                class_average=s.class_average,
                class_rank=s.class_rank,
                grade_rank=s.grade_rank,
                is_absent=bool(s.is_absent),
            )
        )
    return result


@router.get("", response_model=List[ExamListItemOut])
def get_exam_list(
    exam_type: Optional[str] = Query(None, description="按考试类型筛选"),
    db: Session = Depends(get_db),
):
    """获取所有考试列表（按考试日期降序排列）"""
    query = db.query(ExamRecord)
    if exam_type:
        query = query.filter(ExamRecord.exam_type == exam_type)
    exams = query.order_by(ExamRecord.exam_date.desc(), ExamRecord.id.desc()).all()

    output = []
    for ex in exams:
        scores_out = _format_exam_scores_out(ex.scores)
        absent_count = sum(1 for s in ex.scores if s.is_absent)
        rate = _calc_rate(ex.total_score, ex.total_full_score)
        output.append(
            ExamListItemOut(
                id=ex.id,
                title=ex.title,
                exam_type=ex.exam_type or "期中",
                exam_date=ex.exam_date,
                total_score=ex.total_score,
                total_full_score=ex.total_full_score,
                rate=rate,
                class_rank=ex.class_rank,
                grade_rank=ex.grade_rank,
                subject_count=len(ex.scores),
                absent_count=absent_count,
                scores=scores_out,
                created_at=ex.created_at,
            )
        )
    return output


@router.post("", response_model=ExamDetailOut)
def create_exam(body: ExamCreateIn, db: Session = Depends(get_db)):
    """录入新考试及各科分数（单事务落库，缺考科目分子分母均不计入总分）"""
    total_score = 0.0
    total_full = 0.0
    valid_score_count = 0

    scores_to_add = []
    for s_in in body.scores:
        is_abs = bool(s_in.is_absent)
        score_val = s_in.score if not is_abs else None

        # 既未标记缺考、也未填分数的科目视为本次未考科目，不写入明细
        if not is_abs and score_val is None:
            continue

        if not is_abs and score_val is not None:
            total_score += score_val
            total_full += s_in.full_score
            valid_score_count += 1

        scores_to_add.append(
            ExamScore(
                subject_id=s_in.subject_id,
                score=score_val,
                full_score=s_in.full_score,
                class_average=s_in.class_average,
                class_rank=s_in.class_rank,
                grade_rank=s_in.grade_rank,
                is_absent=is_abs,
            )
        )

    final_total = round(total_score, 1) if valid_score_count > 0 else None
    final_full = round(total_full, 1) if valid_score_count > 0 else None

    exam = ExamRecord(
        student_id=1,
        title=body.title.strip(),
        exam_type=body.exam_type or "期中",
        exam_date=body.exam_date,
        total_score=final_total,
        total_full_score=final_full,
        class_rank=body.class_rank,
        grade_rank=body.grade_rank,
        remarks=body.remarks,
    )
    exam.scores = scores_to_add

    db.add(exam)
    db.commit()
    db.refresh(exam)

    scores_out = _format_exam_scores_out(exam.scores)
    return ExamDetailOut(
        id=exam.id,
        student_id=exam.student_id,
        title=exam.title,
        exam_type=exam.exam_type or "期中",
        exam_date=exam.exam_date,
        total_score=exam.total_score,
        total_full_score=exam.total_full_score,
        rate=_calc_rate(exam.total_score, exam.total_full_score),
        class_rank=exam.class_rank,
        grade_rank=exam.grade_rank,
        remarks=exam.remarks,
        scores=scores_out,
        created_at=exam.created_at,
    )


@router.get("/{exam_id}", response_model=ExamDetailOut)
def get_exam_detail(exam_id: int, db: Session = Depends(get_db)):
    """获取指定考试详情与各科成绩明细"""
    exam = db.query(ExamRecord).filter(ExamRecord.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail=f"考试记录不存在 (id={exam_id})")

    scores_out = _format_exam_scores_out(exam.scores)
    return ExamDetailOut(
        id=exam.id,
        student_id=exam.student_id,
        title=exam.title,
        exam_type=exam.exam_type or "期中",
        exam_date=exam.exam_date,
        total_score=exam.total_score,
        total_full_score=exam.total_full_score,
        rate=_calc_rate(exam.total_score, exam.total_full_score),
        class_rank=exam.class_rank,
        grade_rank=exam.grade_rank,
        remarks=exam.remarks,
        scores=scores_out,
        created_at=exam.created_at,
    )


@router.put("/{exam_id}", response_model=ExamDetailOut)
def update_exam(exam_id: int, body: ExamUpdateIn, db: Session = Depends(get_db)):
    """修改考试与科目成绩（单事务原子替换，无冗余补丁复杂度）"""
    exam = db.query(ExamRecord).filter(ExamRecord.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail=f"考试记录不存在 (id={exam_id})")

    if body.title is not None:
        exam.title = body.title.strip()
    if body.exam_type is not None:
        exam.exam_type = body.exam_type
    if body.exam_date is not None:
        exam.exam_date = body.exam_date
    if body.class_rank is not None:
        exam.class_rank = body.class_rank
    if body.grade_rank is not None:
        exam.grade_rank = body.grade_rank
    if body.remarks is not None:
        exam.remarks = body.remarks

    if body.scores is not None:
        # 清除既有成绩，重新插入新成绩
        db.query(ExamScore).filter(ExamScore.exam_id == exam_id).delete()

        total_score = 0.0
        total_full = 0.0
        valid_score_count = 0
        new_scores = []

        for s_in in body.scores:
            is_abs = bool(s_in.is_absent)
            score_val = s_in.score if not is_abs else None

            # 既未标记缺考、也未填分数的科目视为本次未考科目，不写入明细
            if not is_abs and score_val is None:
                continue

            if not is_abs and score_val is not None:
                total_score += score_val
                total_full += s_in.full_score
                valid_score_count += 1

            new_scores.append(
                ExamScore(
                    exam_id=exam_id,
                    subject_id=s_in.subject_id,
                    score=score_val,
                    full_score=s_in.full_score,
                    class_average=s_in.class_average,
                    class_rank=s_in.class_rank,
                    grade_rank=s_in.grade_rank,
                    is_absent=is_abs,
                )
            )

        db.add_all(new_scores)
        exam.total_score = round(total_score, 1) if valid_score_count > 0 else None
        exam.total_full_score = round(total_full, 1) if valid_score_count > 0 else None

    db.commit()
    db.refresh(exam)

    scores_out = _format_exam_scores_out(exam.scores)
    return ExamDetailOut(
        id=exam.id,
        student_id=exam.student_id,
        title=exam.title,
        exam_type=exam.exam_type or "期中",
        exam_date=exam.exam_date,
        total_score=exam.total_score,
        total_full_score=exam.total_full_score,
        rate=_calc_rate(exam.total_score, exam.total_full_score),
        class_rank=exam.class_rank,
        grade_rank=exam.grade_rank,
        remarks=exam.remarks,
        scores=scores_out,
        created_at=exam.created_at,
    )


@router.delete("/{exam_id}")
def delete_exam(exam_id: int, db: Session = Depends(get_db)):
    """删除考试（级联删除所有科目得分）"""
    exam = db.query(ExamRecord).filter(ExamRecord.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail=f"考试记录不存在 (id={exam_id})")

    db.delete(exam)
    db.commit()
    return {"message": "考试记录已成功删除", "exam_id": exam_id}


# --------------------------------------------------------------------------
# 图表数据源与学情分析接口
# --------------------------------------------------------------------------

@router.get("/charts/trends", response_model=ExamTrendsOut)
def get_exam_trends(
    subject_id: Optional[int] = Query(None, description="学科 ID，不传查全科总分走势"),
    db: Session = Depends(get_db),
):
    """
    走势折线图数据源：按时间升序输出实得分与满分率走势。
    当只有 1 次考试时安全输出单点，绝不崩溃。
    """
    exams = db.query(ExamRecord).order_by(ExamRecord.exam_date.asc(), ExamRecord.id.asc()).all()
    if not exams:
        return ExamTrendsOut(target="total", subject_id=None, items=[])

    if subject_id is None:
        # 总分走势
        items = []
        for ex in exams:
            rate = _calc_rate(ex.total_score, ex.total_full_score)
            items.append(
                ExamTrendsItemOut(
                    exam_id=ex.id,
                    title=ex.title,
                    exam_type=ex.exam_type or "期中",
                    exam_date=ex.exam_date,
                    score=ex.total_score,
                    full_score=ex.total_full_score,
                    rate=rate,
                    class_rank=ex.class_rank,
                    grade_rank=ex.grade_rank,
                    is_absent=False,
                )
            )
        return ExamTrendsOut(target="total", subject_id=None, items=items)
    else:
        # 单科走势
        subject = db.query(Subject).filter(Subject.id == subject_id).first()
        sub_name = subject.name if subject else f"科目{subject_id}"

        items = []
        for ex in exams:
            score_rec = next((s for s in ex.scores if s.subject_id == subject_id), None)
            if not score_rec:
                continue

            rate = _calc_rate(score_rec.score, score_rec.full_score) if not score_rec.is_absent else None
            items.append(
                ExamTrendsItemOut(
                    exam_id=ex.id,
                    title=ex.title,
                    exam_type=ex.exam_type or "期中",
                    exam_date=ex.exam_date,
                    score=score_rec.score if not score_rec.is_absent else None,
                    full_score=score_rec.full_score,
                    rate=rate,
                    class_rank=score_rec.class_rank,
                    grade_rank=score_rec.grade_rank,
                    is_absent=bool(score_rec.is_absent),
                )
            )
        return ExamTrendsOut(target=sub_name, subject_id=subject_id, items=items)


@router.get("/charts/radar", response_model=ExamRadarOut)
def get_exam_radar(
    exam_id: Optional[int] = Query(None, description="指定考试 ID，不传默认取最近一次全科考试"),
    db: Session = Depends(get_db),
):
    """
    学力均衡雷达图数据源：
    动态指标轴（缺考科不入轴），下方列出缺考提示；实考少于 3 门展示友好提示。
    """
    if exam_id:
        exam = db.query(ExamRecord).filter(ExamRecord.id == exam_id).first()
    else:
        # 默认取包含科目数最多且最近的一场考试
        exams = db.query(ExamRecord).order_by(ExamRecord.exam_date.desc(), ExamRecord.id.desc()).all()
        # 优先选实考 >= 3 科的最近考试
        exam = None
        for ex in exams:
            valid_cnt = sum(1 for s in ex.scores if not s.is_absent and s.score is not None)
            if valid_cnt >= 3:
                exam = ex
                break
        if not exam and exams:
            exam = exams[0]

    if not exam:
        return ExamRadarOut(message="暂无考试记录")

    indicators = []
    values = []
    absent_subjects = []

    # 优先按 CORE_7_SUBJECTS 顺序排，其他科置后
    def _sub_rank(s: ExamScore):
        sub_name = s.subject.name if s.subject else ""
        if sub_name in CORE_7_SUBJECTS:
            return (0, CORE_7_SUBJECTS.index(sub_name))
        return (1, s.subject_id)

    sorted_scores = sorted(exam.scores, key=_sub_rank)

    for s in sorted_scores:
        sub_name = s.subject.name if s.subject else f"科目{s.subject_id}"
        if s.is_absent or s.score is None:
            absent_subjects.append(sub_name)
        else:
            rate = _calc_rate(s.score, s.full_score) or 0.0
            indicators.append(RadarIndicatorOut(subject_id=s.subject_id, name=sub_name, max=100.0))
            values.append(rate)

    msg = None
    if len(indicators) < 3:
        msg = "实考科目不足 3 门，无法生成雷达多边形"

    return ExamRadarOut(
        exam_id=exam.id,
        exam_title=exam.title,
        exam_date=exam.exam_date,
        indicators=indicators,
        values=values,
        absent_subjects=absent_subjects,
        message=msg,
    )


@router.get("/diagnostics/weaknesses", response_model=List[SubjectWeaknessItemOut])
def get_subject_weaknesses(db: Session = Depends(get_db)):
    """
    薄弱学科智能诊断：
    规则：最近考试得分率 < 60% 或 错题本中未掌握错题 >= 3 判定为薄弱学科。
    """
    subjects = db.query(Subject).all()
    # 取最近 3 场考试评估成绩
    recent_exams = db.query(ExamRecord).order_by(ExamRecord.exam_date.desc()).limit(3).all()
    recent_exam_ids = [ex.id for ex in recent_exams]

    results = []
    for sub in subjects:
        # 1. 计算最近考试平均得分率
        scores = (
            db.query(ExamScore)
            .filter(
                ExamScore.subject_id == sub.id,
                ExamScore.exam_id.in_(recent_exam_ids),
                ExamScore.is_absent == False,
                ExamScore.score.isnot(None),
            )
            .all()
        )
        avg_rate = None
        if scores:
            rates = [s.score / s.full_score * 100 for s in scores if s.full_score > 0]
            if rates:
                avg_rate = round(sum(rates) / len(rates), 1)

        # 2. 统计错题本中该科未掌握错题数 (review_count >= 2 或 mastery_status != '已掌握')
        unmastered_count = (
            db.query(MistakeRecord)
            .filter(
                MistakeRecord.subject_id == sub.id,
                MistakeRecord.mastery_status != "已掌握",
            )
            .count()
        )

        # 3. 极简规则判定薄弱
        is_weak = False
        reasons = []
        if avg_rate is not None and avg_rate < 60.0:
            is_weak = True
            reasons.append(f"近期考试平均满分率仅 {avg_rate}%（不及格）")
        if unmastered_count >= 3:
            is_weak = True
            reasons.append(f"错题本堆积 {unmastered_count} 道未掌握顽固题")

        if is_weak or sub.name in CORE_7_SUBJECTS:
            results.append(
                SubjectWeaknessItemOut(
                    subject_id=sub.id,
                    subject_name=sub.name,
                    recent_rate=avg_rate,
                    unmastered_mistakes_count=unmastered_count,
                    is_weak=is_weak,
                    reason="；".join(reasons) if reasons else "学科基础较扎实",
                )
            )

    # 优先将薄弱学科排在最前面
    results.sort(key=lambda x: (not x.is_weak, -(x.unmastered_mistakes_count or 0)))
    return results


@router.get("/analytics/monthly", response_model=MonthlyAnalyticsOut)
def get_monthly_analytics(
    year: Optional[int] = Query(None, description="年份，默认当年"),
    month: Optional[int] = Query(None, description="月份，默认当月"),
    db: Session = Depends(get_db),
):
    """
    家长空间月度学情看板：
    全月每日完成率曲线 + 各科目未完成频次分布（柱状图）
    """
    now = datetime.now(SHANGHAI_TZ)
    target_year = year or now.year
    target_month = month or now.month

    _, num_days = calendar.monthrange(target_year, target_month)
    start_date = date(target_year, target_month, 1)
    end_date = date(target_year, target_month, num_days)

    # 查询当月所有作业记录
    hw_items = (
        db.query(HomeworkItem)
        .filter(HomeworkItem.date >= start_date, HomeworkItem.date <= end_date)
        .all()
    )

    day_map = {}
    for d in range(1, num_days + 1):
        d_str = f"{target_year}-{target_month:02d}-{d:02d}"
        day_map[d_str] = {"total": 0, "completed": 0}

    missing_by_subject = {}
    for item in hw_items:
        d_str = item.date.strftime("%Y-%m-%d")
        if d_str in day_map:
            day_map[d_str]["total"] += 1
            if item.is_completed:
                day_map[d_str]["completed"] += 1
            else:
                sub_id = item.subject_id
                missing_by_subject[sub_id] = missing_by_subject.get(sub_id, 0) + 1

    daily_trends = []
    recorded_days = 0
    perfect_days = 0
    total_rates = []

    for d_str, val in sorted(day_map.items()):
        total = val["total"]
        completed = val["completed"]
        if total > 0:
            recorded_days += 1
            rate = int(completed / total * 100)
            if rate == 100:
                perfect_days += 1
            total_rates.append(rate)
        else:
            rate = 0
        daily_trends.append(
            DailyCompletionItemOut(
                date=d_str,
                rate=rate,
                total=total,
                completed=completed,
            )
        )

    avg_rate = round(sum(total_rates) / len(total_rates), 1) if total_rates else 0.0

    # 查出科目名称
    subjects = db.query(Subject).all()
    sub_name_map = {s.id: s.name for s in subjects}

    missing_distribution = []
    for sub_id, count in sorted(missing_by_subject.items(), key=lambda x: -x[1]):
        missing_distribution.append(
            SubjectMissingCountOut(
                subject_id=sub_id,
                subject_name=sub_name_map.get(sub_id, f"科目{sub_id}"),
                missing_count=count,
            )
        )

    return MonthlyAnalyticsOut(
        year=target_year,
        month=target_month,
        total_days=num_days,
        recorded_days=recorded_days,
        perfect_days=perfect_days,
        average_completion_rate=avg_rate,
        daily_trends=daily_trends,
        subject_missing_distribution=missing_distribution,
    )
