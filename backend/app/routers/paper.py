import json
import math
import random
import re
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
    PaperEstimateOut,
)

router = APIRouter(prefix="/api/paper", tags=["A4 周末重练卷"])

# 初一预置核心 7 科白名单
CORE_7_SUBJECTS = ["数学", "语文", "英语", "道法", "历史", "地理", "生物"]


# ---------------------------------------------------------------------------
# 答题留白分级（按题型）
#
# 背景：早期实现把「紧凑/标准/宽敞」当成整卷唯一常量（30/45/60mm）套给每一题，
# 于是选择题、默写题这类只需写几个字的题目也白占 45mm，整卷留白浪费过半。
# 现在改为两步：先按题干特征判定题型基线，再乘以整卷松紧系数。
#
# 刻意不使用 MistakeRecord.answer 的字数作为信号 —— 实测 18 条错题里仅 8 条有答案，
# 且选择题答案为 "A"（1 字）、默写答案为 8~11 字，字数与所需书写量完全不成正比。
# 答案字段本身也不得进入任何打印输出（见 compose_paper 中的说明）。
# ---------------------------------------------------------------------------

# 题型基线留白（mm）。全部取 8mm 整数倍，正好对齐 print.css 的 8mm 方格底纹，
# 避免出现半行网格（旧的固定 45mm = 5.6 行，末行即被切掉一半）。
BLANK_TIER_BASE_MM = {
    "choice": 16,    # 选择题：只需写选项字母
    "judge": 24,     # 判断题：写「对/错」，常需补一句说明
    "recite": 24,    # 默写 / 听写 / 填空：2~3 行书写
    "short": 32,     # 无明确特征：保守兜底
    "essay": 48,     # 简答 / 说明理由 / 材料分析：需成段作答
    "solution": 48,  # 解答 / 计算 / 证明：需写过程
}

BLANK_TIER_LABEL = {
    "choice": "选择题",
    "judge": "判断题",
    "recite": "默写/听写",
    "short": "常规",
    "essay": "简答/说明",
    "solution": "解答/计算",
}

# 整卷松紧：三档由「固定值」改为「整体系数」，保住整卷统一调松紧的能力
SPACE_LEVEL_FACTOR = {"compact": 0.7, "standard": 1.0, "spacious": 1.35}
BLANK_MIN_MM = 16
BLANK_MAX_MM = 64
BLANK_STEP_MM = 8  # 与 8mm 方格底纹对齐

_RE_OPTION_MARK = re.compile(r"[A-DＡ-Ｄ]\s*[．.、]")
_RE_EMPTY_BRACKET = re.compile(r"[（(]\s*[)）]")
_RE_RECITE = re.compile(r"默写|听写|填空|填写|写出")
_RE_ESSAY = re.compile(r"说明理由|简述|谈谈|你的看法|有何意义|分析|为什么|原因")
_RE_JUDGE = re.compile(r"判断|是否正确|说法正确|说法错误")
_RE_SOLVE = re.compile(r"计算|解方程|解不等式|求证|证明|求")
_SOLVE_SUBJECTS = {"数学", "物理", "化学"}


def _infer_blank_tier(
    text: Optional[str], subject_name: Optional[str], has_image: bool = False
) -> str:
    """按题干特征判定题型，用于决定该题答题留白高度。

    判定顺序即优先级：选择题放在最前，因为它的选项文本里常出现「分析」「判断」
    这类会被后续规则误命中的词（如生物题选项「A．解剖和分析」）。
    """
    content = text or ""

    # 1) 选择题：两处以上选项标记，或「（）」配合至少一处选项标记
    option_count = len(_RE_OPTION_MARK.findall(content))
    if option_count >= 2 or (option_count >= 1 and _RE_EMPTY_BRACKET.search(content)):
        return "choice"
    # 2) 默写 / 听写 / 填空
    if _RE_RECITE.search(content):
        return "recite"
    # 3) 简答 / 说明理由 / 材料分析
    if _RE_ESSAY.search(content):
        return "essay"
    # 4) 判断题
    if _RE_JUDGE.search(content):
        return "judge"
    # 5) 解答 / 计算类，或带配图的作图/读图题
    if (subject_name in _SOLVE_SUBJECTS and _RE_SOLVE.search(content)) or has_image:
        return "solution"
    # 6) 兜底
    return "short"


def _calc_space_mm(tier: str, space_level: str) -> int:
    """题型基线 × 整卷松紧系数，对齐 8mm 网格并夹取到安全区间。"""
    base = BLANK_TIER_BASE_MM.get(tier, BLANK_TIER_BASE_MM["short"])
    factor = SPACE_LEVEL_FACTOR.get(space_level, 1.0)
    stepped = int(math.floor(base * factor / BLANK_STEP_MM + 0.5)) * BLANK_STEP_MM
    return max(BLANK_MIN_MM, min(BLANK_MAX_MM, stepped))


# A4 版式常量：与 frontend/src/assets/print.css 的 @page 边距/图片 max-height 同口径
PAGE_CONTENT_MM = 261.0      # A4 高 297mm - 上下各 18mm 页边距
FIRST_PAGE_HEADER_MM = 90.0  # 大标题 + 考生信息 + 得分表 + 考生须知
QUESTION_CHROME_MM = 12.0    # 题号行 + 题间距（print.css 中 margin-bottom: 22px）
TEXT_LINE_MM = 5.5           # 题干行高（10.5pt × 1.6）
TEXT_CHARS_PER_LINE = 40
DIAGRAM_RESERVED_MM = 55.0   # 与 print.css 的 max-height: 55mm 同口径


def _question_height_mm(text: Optional[str], space_mm: int, has_image: bool) -> float:
    """单题在纸面上的估算占地高度（mm）：题号行 + 题干 + 配图 + 留白。"""
    content = text or ""
    if content:
        lines = math.ceil(len(content) / TEXT_CHARS_PER_LINE)
        text_h = max(TEXT_LINE_MM, lines * TEXT_LINE_MM)
    else:
        text_h = 0.0
    return QUESTION_CHROME_MM + text_h + (DIAGRAM_RESERVED_MM if has_image else 0.0) + space_mm


def _calc_estimated_pages(question_heights_mm: List[float]) -> int:
    """按逐题实际高度估算页数。

    旧版是 round(题数/4) + ceil(图数/6)，与真实排版脱节：留白分级后题高差异很大，
    按题数取平均会明显偏离。此处改为按 mm 求和后与 A4 可用高度相除。
    """
    total = sum(question_heights_mm)
    if total <= 0:
        return 1
    return max(1, math.ceil((total + FIRST_PAGE_HEADER_MM) / PAGE_CONTENT_MM))


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
                cropped_diagram_path=r.cropped_diagram_path,
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
    student_name = student.name if student else "王昱轩同学"

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

    questions = []
    warnings = []
    question_heights: List[float] = []

    for idx, r in enumerate(ordered_records):
        # 打印只使用"题目配图"（数轴/几何图等图形）。
        # 题干整图（original_image_path）是孩子试卷的裁剪照，常带手写订正笔迹，
        # 印到复习卷上等于直接给答案，故一律不输出。
        diagram_url = r.cropped_diagram_path
        has_img = bool(diagram_url)

        is_oversized = _check_oversized(r.extracted_text, body.space_level, has_image=has_img)
        if is_oversized:
            warnings.append(f"第 {idx + 1} 题题干内容较长，可能跨页显示")

        subject_name = r.subject.name if r.subject else None
        sub_display = _resolve_subject_display(subject_name)

        # 逐题判定题型并换算留白：选择题 16mm、默写 24mm、解答/简答 48mm…
        blank_tier = _infer_blank_tier(r.extracted_text, subject_name, has_image=has_img)
        space_mm = _calc_space_mm(blank_tier, body.space_level)
        question_heights.append(_question_height_mm(r.extracted_text, space_mm, has_img))

        questions.append(
            PaperQuestionOut(
                id=r.id,
                order_num=idx + 1,
                subject_id=r.subject_id,
                subject_name=sub_display,
                extracted_text=r.extracted_text,
                original_image_path=None,
                diagram_image_path=diagram_url,
                error_type=r.error_type if body.show_error_type else None,
                space_mm=space_mm,
                blank_tier=blank_tier,
                is_oversized=is_oversized,
            )
        )

    total_q = len(questions)
    estimated_pages = _calc_estimated_pages(question_heights)

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
# 路由匹配关键顺序守卫：静态具体路由 /history、/estimate 必须注册在
# 动态参数路由 /{paper_id} 之前！否则会被当成 paper_id 解析为 int 报 422。
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


@router.get("/estimate", response_model=PaperEstimateOut)
def estimate_paper_pages(
    ids: str = Query("", description="逗号分隔的错题 ID，如 1,2,3"),
    space_level: str = Query("standard", description="compact / standard / spacious"),
    db: Session = Depends(get_db),
):
    """
    组卷前的页数预估（只读，不落库）。

    抽成接口是为了让配置页的「预计 X 页」和真实出卷共用同一套留白与页数规则。
    此前前端自带一份 round(题数/4)+ceil(图数/6) 的副本，留白改为逐题分级后
    两者必然漂移，故统一到此处。
    """
    try:
        mistake_ids = [int(x) for x in ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=422, detail="ids 需为逗号分隔的整数")

    if not mistake_ids:
        return PaperEstimateOut(estimated_pages=1, total_questions=0)

    records = db.query(MistakeRecord).filter(MistakeRecord.id.in_(mistake_ids)).all()

    heights: List[float] = []
    for r in records:
        has_img = bool(r.cropped_diagram_path)
        tier = _infer_blank_tier(
            r.extracted_text, r.subject.name if r.subject else None, has_image=has_img
        )
        heights.append(
            _question_height_mm(
                r.extracted_text, _calc_space_mm(tier, space_level), has_img
            )
        )

    return PaperEstimateOut(
        estimated_pages=_calc_estimated_pages(heights),
        total_questions=len(records),
    )


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

    space_level = paper.space_level or "standard"
    questions = []
    warnings = json.loads(paper.warnings or "[]")

    for idx, mid in enumerate(mistake_ids):
        if mid not in record_map:
            continue
        r = record_map[mid]
        # 同 compose：打印只输出题目配图，绝不输出可能带订正笔迹的题干整图
        diagram_url = r.cropped_diagram_path
        has_img = bool(diagram_url)
        is_oversized = _check_oversized(r.extracted_text, space_level, has_image=has_img)
        subject_name = r.subject.name if r.subject else None
        sub_display = _resolve_subject_display(subject_name)

        # 与 compose 走同一套分级规则，保证复看时留白与出卷当时完全一致
        blank_tier = _infer_blank_tier(r.extracted_text, subject_name, has_image=has_img)
        space_mm = _calc_space_mm(blank_tier, space_level)

        questions.append(
            PaperQuestionOut(
                id=r.id,
                order_num=idx + 1,
                subject_id=r.subject_id,
                subject_name=sub_display,
                extracted_text=r.extracted_text,
                original_image_path=None,
                diagram_image_path=diagram_url,
                error_type=r.error_type if paper.show_error_type else None,
                space_mm=space_mm,
                blank_tier=blank_tier,
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


@router.delete("/{paper_id}")
def delete_paper(paper_id: int, db: Session = Depends(get_db)):
    """
    删除一条历史组卷记录（不可恢复）。

    安全性说明：papers 表只持有 mistake_ids 的 JSON 快照，不持有任何外键；
    重练打卡流水落在独立的 mistake_reviews 表并已推进 MistakeRecord 的复习轮次。
    因此删除试卷不会影响错题本身，也不会回退艾宾浩斯进度。
    """
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail=f"试卷不存在 (id={paper_id})")

    db.delete(paper)
    db.commit()

    return {"paper_id": paper_id, "deleted": True}
