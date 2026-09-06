import json
import math
import random
from datetime import datetime, date, time, timedelta
from typing import List, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import MistakeRecord, MistakeReview, Subject, Student, Paper
from backend.app.schemas import (
    PaperCandidateOut,
    PaperComposeIn,
    PaperQuestionOut,
    PaperComposeOut,
    PaperBatchReviewIn,
    PaperBatchReviewOut,
    PaperBatchReviewFailedItem,
    PaperHistoryOut,
)

router = APIRouter(prefix="/api/paper", tags=["A4 周末重练卷"])

# 初一预置核心 7 科白名单
CORE_7_SUBJECTS = ["数学", "语文", "英语", "道德与法治", "历史", "地理", "生物"]


def _calc_space_mm(space_level: str) -> int:
    if space_level == "compact":
        return 30
    elif space_level == "spacious":
        return 60
    return 45  # standard (默认 >= 40mm)


def _calc_estimated_pages(total_questions: int, image_count: int) -> int:
    if total_questions <= 0:
        return 1
    return max(1, round(total_questions / 4) + math.ceil(image_count / 6))


def _check_oversized(text: Optional[str], space_level: str, has_image: bool = False) -> bool:
    content = text or ""
    text_len = len(content)
    if text_len >= 800:
        return True
    if has_image and text_len >= 500:
        return True
    if space_level == "spacious" and text_len >= 400:
        return True
    if space_level == "spacious" and has_image and text_len >= 250:
        return True
    return False


def _resolve_subject_display(sub_name: Optional[str]) -> str:
    """非 7 科错题（如艺术、信息科技等）按规范归入'综合'大题"""
    if not sub_name:
        return "综合"
    return sub_name if sub_name in CORE_7_SUBJECTS else "综合"


@router.get("/candidates", response_model=List[PaperCandidateOut])
def get_paper_candidates(
    preset: str = Query("all", description="预设过滤: this_week, ebbinghaus, unmastered, all"),
    subject_id: Optional[int] = Query(None, description="学科 ID 过滤，不传查全科"),
    error_type: Optional[str] = Query(None, description="错因类型过滤"),
    include_all_subjects: bool = Query(False, description="是否包含非核心7科的全部科目"),
    limit: int = Query(100, description="最大返回条数"),
    db: Session = Depends(get_db),
):
    """
    获取组卷候选错题列表。
    默认过滤至初一核心 7 科，设置 include_all_subjects=True 可纳入美术/信息等全科。
    """
    now_shanghai = datetime.now(ZoneInfo("Asia/Shanghai"))
    today = now_shanghai.date()
    monday = today - timedelta(days=today.weekday())
    monday_start = datetime.combine(monday, time.min)

    query = db.query(MistakeRecord).join(Subject, MistakeRecord.subject_id == Subject.id)

    if subject_id is not None:
        query = query.filter(MistakeRecord.subject_id == subject_id)
    elif not include_all_subjects:
        # 默认过滤到核心 7 科
        query = query.filter(Subject.name.in_(CORE_7_SUBJECTS))

    if error_type:
        query = query.filter(MistakeRecord.error_type == error_type)

    if preset == "this_week":
        query = query.filter(MistakeRecord.created_at >= monday_start)
    elif preset == "ebbinghaus":
        query = query.filter(
            MistakeRecord.next_review_date <= today,
            MistakeRecord.mastery_status != "已掌握",
        )
    elif preset == "unmastered":
        query = query.filter(
            MistakeRecord.review_count >= 2,
            MistakeRecord.mastery_status != "已掌握",
        )

    records = query.order_by(Subject.sort_order.asc(), MistakeRecord.id.desc()).limit(limit).all()

    candidates = []
    for r in records:
        is_this_week = bool(r.created_at and r.created_at >= monday_start)
        is_ebbinghaus = bool(
            r.next_review_date and r.next_review_date <= today and r.mastery_status != "已掌握"
        )
        is_unmastered = bool(r.review_count >= 2 and r.mastery_status != "已掌握")

        candidates.append(
            PaperCandidateOut(
                id=r.id,
                subject_id=r.subject_id,
                subject_name=r.subject.name if r.subject else "综合",
                extracted_text=r.extracted_text,
                original_image_path=r.original_image_path,
                thumbnail_path=r.thumbnail_path,
                error_type=r.error_type,
                mastery_status=r.mastery_status,
                review_count=r.review_count,
                next_review_date=r.next_review_date,
                created_at=r.created_at,
                is_this_week=is_this_week,
                is_ebbinghaus=is_ebbinghaus,
                is_unmastered=is_unmastered,
            )
        )

    return candidates


@router.post("/compose", response_model=PaperComposeOut)
def compose_paper(body: PaperComposeIn, db: Session = Depends(get_db)):
    """
    组装 A4 周末重练卷。
    完成题目排序、留白分配、超长题启发式标记与粗略页数估算，
    并将试卷快照落入 papers 表，返回 paper_id。
    """
    student = db.query(Student).filter(Student.id == 1).first()
    student_name = student.name if student else "初一同学"

    if not body.mistake_ids:
        # 空试卷防护
        paper = Paper(
            title=body.title,
            subtitle=body.subtitle,
            mistake_ids=json.dumps([]),
            sort_by=body.sort_by,
            space_level=body.space_level,
            style_mode=body.style_mode,
            show_error_type=body.show_error_type,
            estimated_pages=1,
            warnings=json.dumps([]),
            student_name=student_name,
            status="draft",
        )
        db.add(paper)
        db.commit()
        db.refresh(paper)
        return PaperComposeOut(
            paper_id=paper.id,
            title=paper.title,
            subtitle=paper.subtitle,
            student_name=student_name,
            sort_by=body.sort_by,
            space_level=body.space_level,
            style_mode=body.style_mode,
            show_error_type=body.show_error_type,
            questions=[],
            total_questions=0,
            estimated_pages=1,
            warnings=[],
            status="draft",
            created_at=paper.created_at,
        )

    # 查出所有对应错题
    records = db.query(MistakeRecord).filter(MistakeRecord.id.in_(body.mistake_ids)).all()
    record_map = {r.id: r for r in records}

    # 排序决策
    if body.sort_by == "subject":
        # 核心7科按 sort_order 排在前，非核心科置于末尾归入综合
        ordered_records = sorted(
            [record_map[mid] for mid in body.mistake_ids if mid in record_map],
            key=lambda r: (
                r.subject.sort_order if (r.subject and r.subject.name in CORE_7_SUBJECTS) else 999,
                r.id,
            ),
        )
    elif body.sort_by == "random":
        ordered_records = [record_map[mid] for mid in body.mistake_ids if mid in record_map]
        random.shuffle(ordered_records)
    else:
        # "order" 或默认：保持用户勾选/传入顺序
        ordered_records = [record_map[mid] for mid in body.mistake_ids if mid in record_map]

    space_mm = _calc_space_mm(body.space_level)
    questions = []
    warnings = []
    image_count = 0

    for idx, r in enumerate(ordered_records):
        has_img = bool(r.original_image_path or r.thumbnail_path)
        if has_img:
            image_count += 1

        is_oversized = _check_oversized(r.extracted_text, body.space_level, has_image=has_img)
        if is_oversized:
            warnings.append(f"第 {idx + 1} 题题干内容较长，可能跨页显示")

        # 确保使用高清原图 URL，避免 320px 缩略图
        img_url = r.original_image_path or r.thumbnail_path
        sub_display = _resolve_subject_display(r.subject.name if r.subject else None)

        questions.append(
            PaperQuestionOut(
                id=r.id,
                order_num=idx + 1,
                subject_id=r.subject_id,
                subject_name=sub_display,
                extracted_text=r.extracted_text,
                original_image_path=img_url,
                error_type=r.error_type if body.show_error_type else None,
                space_mm=space_mm,
                is_oversized=is_oversized,
            )
        )

    total_q = len(questions)
    estimated_pages = _calc_estimated_pages(total_q, image_count)

    # 落 papers 表
    ordered_ids = [q.id for q in questions]
    paper = Paper(
        title=body.title,
        subtitle=body.subtitle,
        mistake_ids=json.dumps(ordered_ids),
        sort_by=body.sort_by,
        space_level=body.space_level,
        style_mode=body.style_mode,
        show_error_type=body.show_error_type,
        estimated_pages=estimated_pages,
        warnings=json.dumps(warnings, ensure_ascii=False),
        student_name=student_name,
        status="draft",
    )
    db.add(paper)
    db.commit()
    db.refresh(paper)

    return PaperComposeOut(
        paper_id=paper.id,
        title=paper.title,
        subtitle=paper.subtitle,
        student_name=student_name,
        sort_by=body.sort_by,
        space_level=body.space_level,
        style_mode=body.style_mode,
        show_error_type=body.show_error_type,
        questions=questions,
        total_questions=total_q,
        estimated_pages=estimated_pages,
        warnings=warnings,
        status=paper.status,
        created_at=paper.created_at,
    )


# --------------------------------------------------------------------------
# 路由匹配关键顺序守卫：静态具体路由 /history 必须注册在动态参数路由 /{paper_id} 之前！
# --------------------------------------------------------------------------
@router.get("/history", response_model=List[PaperHistoryOut])
def get_paper_history(
    limit: int = Query(20, description="最大返回记录数"),
    status: Optional[str] = Query(None, description="状态过滤: draft, printed, reviewed"),
    db: Session = Depends(get_db),
):
    """
    获取历史组卷记录列表。
    必须在 /{paper_id} 之前注册，防止被当成 paper_id 解析为 int 报 422。
    """
    query = db.query(Paper)
    if status:
        query = query.filter(Paper.status == status)

    papers = query.order_by(Paper.created_at.desc()).limit(limit).all()

    history = []
    for p in papers:
        ids = json.loads(p.mistake_ids or "[]")
        history.append(
            PaperHistoryOut(
                id=p.id,
                title=p.title,
                subtitle=p.subtitle,
                student_name=p.student_name,
                total_questions=len(ids),
                estimated_pages=p.estimated_pages or 1,
                status=p.status or "draft",
                created_at=p.created_at,
            )
        )

    return history


@router.get("/{paper_id}", response_model=PaperComposeOut)
def get_paper_by_id(paper_id: int, db: Session = Depends(get_db)):
    """
    凭 paper_id 恢复试卷快照，供 F5 刷新、多设备访问与历史复看使用。
    """
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail=f"试卷不存在 (id={paper_id})")

    mistake_ids: List[int] = json.loads(paper.mistake_ids or "[]")
    records = db.query(MistakeRecord).filter(MistakeRecord.id.in_(mistake_ids)).all()
    record_map = {r.id: r for r in records}

    space_mm = _calc_space_mm(paper.space_level or "standard")
    questions = []
    warnings = json.loads(paper.warnings or "[]")

    for idx, mid in enumerate(mistake_ids):
        if mid not in record_map:
            continue
        r = record_map[mid]
        has_img = bool(r.original_image_path or r.thumbnail_path)
        is_oversized = _check_oversized(
            r.extracted_text, paper.space_level or "standard", has_image=has_img
        )
        img_url = r.original_image_path or r.thumbnail_path
        sub_display = _resolve_subject_display(r.subject.name if r.subject else None)

        questions.append(
            PaperQuestionOut(
                id=r.id,
                order_num=idx + 1,
                subject_id=r.subject_id,
                subject_name=sub_display,
                extracted_text=r.extracted_text,
                original_image_path=img_url,
                error_type=r.error_type if paper.show_error_type else None,
                space_mm=space_mm,
                is_oversized=is_oversized,
            )
        )

    return PaperComposeOut(
        paper_id=paper.id,
        title=paper.title,
        subtitle=paper.subtitle,
        student_name=paper.student_name,
        sort_by=paper.sort_by or "subject",
        space_level=paper.space_level or "standard",
        style_mode=paper.style_mode or "grid",
        show_error_type=bool(paper.show_error_type),
        questions=questions,
        total_questions=len(questions),
        estimated_pages=paper.estimated_pages or 1,
        warnings=warnings,
        status=paper.status or "draft",
        created_at=paper.created_at,
    )


@router.post("/{paper_id}/mark_printed")
def mark_paper_printed(paper_id: int, db: Session = Depends(get_db)):
    """
    当用户在预览页调起系统打印后回写试卷状态为 printed。
    若试卷已经是 reviewed，则保留 reviewed。
    """
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail=f"试卷不存在 (id={paper_id})")

    if paper.status == "draft":
        paper.status = "printed"
        db.commit()
        db.refresh(paper)

    return {"paper_id": paper.id, "status": paper.status}


@router.post("/{paper_id}/batch_review", response_model=PaperBatchReviewOut)
def batch_review_paper(paper_id: int, body: PaperBatchReviewIn, db: Session = Depends(get_db)):
    """
    单事务批量完成重练打卡。
    依次推进艾宾浩斯复习轮次，并将 papers.status 更新为 reviewed。
    """
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail=f"试卷不存在 (id={paper_id})")

    success_ids: List[int] = []
    failed_items: List[PaperBatchReviewFailedItem] = []

    now = datetime.now()
    today = date.today()

    for item in body.reviews:
        r = db.query(MistakeRecord).filter(MistakeRecord.id == item.mistake_id).first()
        if not r:
            failed_items.append(
                PaperBatchReviewFailedItem(mistake_id=item.mistake_id, reason="错题不存在")
            )
            continue

        if item.result == "remembered":
            r.review_count += 1
            r.last_reviewed_at = now
            if r.review_count == 1:
                r.next_review_date = today + timedelta(days=3)
                r.mastery_status = "待复习"
            elif r.review_count == 2:
                r.next_review_date = today + timedelta(days=7)
                r.mastery_status = "待复习"
            elif r.review_count == 3:
                r.next_review_date = today + timedelta(days=15)
                r.mastery_status = "待复习"
            else:
                r.mastery_status = "已掌握"
                r.next_review_date = None
        elif item.result == "forgotten":
            r.mastery_status = "未掌握"
            r.next_review_date = today + timedelta(days=1)
            r.last_reviewed_at = now
        else:
            failed_items.append(
                PaperBatchReviewFailedItem(
                    mistake_id=item.mistake_id,
                    reason=f"无效的复习结果: {item.result}，需为 remembered 或 forgotten",
                )
            )
            continue

        # 记录复习流水
        rev_log = MistakeReview(
            mistake_id=r.id,
            reviewed_at=now,
            result=item.result,
            next_review_date=r.next_review_date,
        )
        db.add(rev_log)
        success_ids.append(r.id)

    paper.status = "reviewed"
    db.commit()

    return PaperBatchReviewOut(
        paper_id=paper.id,
        success=success_ids,
        failed=failed_items,
        message=f"批量打卡完成：成功 {len(success_ids)} 题，失败 {len(failed_items)} 题",
    )
