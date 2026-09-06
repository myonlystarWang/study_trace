#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学迹 StudyTrace — M5 成绩台账与学情分析 Demo 数据播种脚本
用于在开发与验收阶段注入多场真实考试记录（涵盖全科期中、单科缺考、单科周测等多样化场景）
"""

import sys
from pathlib import Path
from datetime import date, datetime

# 确保能正常导入 backend
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from backend.app.database import SessionLocal
from backend.app.models import Subject, ExamRecord, ExamScore, Student, MistakeRecord
from backend.app.seed import seed_database

def seed_m5_demo():
    seed_database()
    db = SessionLocal()
    try:
        # 清除已有的考试数据与 M5 演示错题防重复
        db.query(ExamScore).delete()
        db.query(ExamRecord).delete()
        db.query(MistakeRecord).filter(MistakeRecord.extracted_text.like("地理经纬网定位与半球判断错题%")).delete()
        db.commit()

        # 读取科目
        subjects = db.query(Subject).all()
        sub_map = {s.name: s for s in subjects}

        student = db.query(Student).filter(Student.id == 1).first()
        if not student:
            student = Student(id=1, name="初一同学", grade="初一")
            db.add(student)
            db.commit()

        # 1. 第一次月考 (全科 7 门)
        ex1 = ExamRecord(
            student_id=1,
            title="初一上学期第一次月考",
            exam_type="月考",
            exam_date=date(2024, 10, 8),
            class_rank=8,
            grade_rank=35,
            remarks="初入初中第一场正规大考，各科节奏掌握良好，地理稍微偏弱。",
        )
        scores_1 = [
            ("数学", 108.0, 120.0, 95.0, 6, 28),
            ("语文", 102.0, 120.0, 98.0, 12, 50),
            ("英语", 114.0, 120.0, 100.0, 4, 15),
            ("道德与法治", 88.0, 100.0, 82.0, 9, 40),
            ("历史", 90.0, 100.0, 80.0, 7, 30),
            ("地理", 75.0, 100.0, 78.0, 18, 85),
            ("生物", 85.0, 100.0, 79.0, 10, 42),
        ]
        total_s1 = 0.0
        total_f1 = 0.0
        for sname, sc, fs, c_avg, c_rnk, g_rnk in scores_1:
            if sname in sub_map:
                total_s1 += sc
                total_f1 += fs
                ex1.scores.append(
                    ExamScore(
                        subject_id=sub_map[sname].id,
                        score=sc,
                        full_score=fs,
                        class_average=c_avg,
                        class_rank=c_rnk,
                        grade_rank=g_rnk,
                        is_absent=False,
                    )
                )
        ex1.total_score = total_s1
        ex1.total_full_score = total_f1

        # 2. 期中考试 (全科 7 门)
        ex2 = ExamRecord(
            student_id=1,
            title="初一上学期期中考试",
            exam_type="期中",
            exam_date=date(2024, 11, 15),
            class_rank=4,
            grade_rank=18,
            remarks="数学压轴题满分，英语听力满分，地理有进步但仍需查缺补漏。",
        )
        scores_2 = [
            ("数学", 116.0, 120.0, 96.0, 2, 10),
            ("语文", 106.0, 120.0, 99.0, 8, 38),
            ("英语", 118.0, 120.0, 102.0, 2, 8),
            ("道德与法治", 92.0, 100.0, 84.0, 5, 22),
            ("历史", 94.0, 100.0, 82.0, 4, 18),
            ("地理", 58.0, 100.0, 76.0, 24, 98),  # 故意设计为 < 60 分以触发薄弱学科
            ("生物", 90.0, 100.0, 81.0, 6, 25),
        ]
        total_s2 = 0.0
        total_f2 = 0.0
        for sname, sc, fs, c_avg, c_rnk, g_rnk in scores_2:
            if sname in sub_map:
                total_s2 += sc
                total_f2 += fs
                ex2.scores.append(
                    ExamScore(
                        subject_id=sub_map[sname].id,
                        score=sc,
                        full_score=fs,
                        class_average=c_avg,
                        class_rank=c_rnk,
                        grade_rank=g_rnk,
                        is_absent=False,
                    )
                )
        ex2.total_score = total_s2
        ex2.total_full_score = total_f2

        # 3. 第二次月考 (含 1 门地理缺考)
        ex3 = ExamRecord(
            student_id=1,
            title="初一上学期第二次月考",
            exam_type="月考",
            exam_date=date(2024, 12, 18),
            class_rank=5,
            grade_rank=22,
            remarks="地理因感冒发烧缺考，其余 6 科发挥平稳。",
        )
        scores_3 = [
            ("数学", 112.0, 120.0, 94.0, 4, 16),
            ("语文", 104.0, 120.0, 97.0, 9, 45),
            ("英语", 117.0, 120.0, 101.0, 3, 11),
            ("道德与法治", 90.0, 100.0, 83.0, 6, 26),
            ("历史", 92.0, 100.0, 81.0, 5, 20),
            ("地理", None, 100.0, 77.0, None, None),  # 缺考
            ("生物", 89.0, 100.0, 80.0, 7, 28),
        ]
        total_s3 = 0.0
        total_f3 = 0.0
        for sname, sc, fs, c_avg, c_rnk, g_rnk in scores_3:
            if sname in sub_map:
                is_abs = (sc is None)
                if not is_abs:
                    total_s3 += sc
                    total_f3 += fs
                ex3.scores.append(
                    ExamScore(
                        subject_id=sub_map[sname].id,
                        score=sc,
                        full_score=fs,
                        class_average=c_avg,
                        class_rank=c_rnk,
                        grade_rank=g_rnk,
                        is_absent=is_abs,
                    )
                )
        ex3.total_score = total_s3
        ex3.total_full_score = total_f3

        # 4. 单科压轴专项周测 (仅数学 1 科)
        ex4 = ExamRecord(
            student_id=1,
            title="期末数学专项模拟周测",
            exam_type="周测",
            exam_date=date(2025, 1, 5),
            class_rank=2,
            grade_rank=7,
            total_score=118.0,
            total_full_score=120.0,
            remarks="期末前全真模拟卷，压轴几何大题全对！",
        )
        ex4.scores.append(
            ExamScore(
                subject_id=sub_map["数学"].id,
                score=118.0,
                full_score=120.0,
                class_average=92.0,
                class_rank=2,
                grade_rank=7,
                is_absent=False,
            )
        )

        db.add_all([ex1, ex2, ex3, ex4])

        # 5. 补充几道地理和道法的未掌握错题，用于验证薄弱学科预警逻辑
        geo_sub = sub_map.get("地理")
        if geo_sub:
            geo_mistakes = [
                MistakeRecord(
                    student_id=1,
                    subject_id=geo_sub.id,
                    extracted_text=f"地理经纬网定位与半球判断错题 {i + 1}",
                    mastery_status="未掌握",
                    review_count=2,
                )
                for i in range(4)
            ]
            db.add_all(geo_mistakes)

        db.commit()
        print("Successfully seeded M5 demo exams (4 exams including full subjects, absent subject, and single-subject quiz).")
    finally:
        db.close()


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    seed_m5_demo()

