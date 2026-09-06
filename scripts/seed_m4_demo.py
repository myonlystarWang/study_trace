import io
import json
import math
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
from PIL import Image, ImageDraw, ImageFont

# 确保能正常导入 backend
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from backend.app.database import SessionLocal
from backend.app.models import Subject, Student, MistakeRecord, Paper
from backend.app.utils.image_handler import save_image_bytes



def create_diagram_1() -> bytes:
    """图1：直角三角形 ABC 与垂线高"""
    im = Image.new("RGB", (600, 400), "white")
    draw = ImageDraw.Draw(im)
    # 直角三角形 ABC: A(100, 320), B(500, 320), C(100, 80)
    draw.polygon([(100, 320), (500, 320), (100, 80)], outline="black", width=3)
    # 直角标记 (100, 320)
    draw.rectangle([100, 295, 125, 320], outline="black", width=2)
    # 垂线 CD 到斜边 AB? 这里 A 是直角，从 A 向 BC 引垂线 AD: 斜边是 BC, D 在 BC 上
    # BC 向量: (400, 240). 垂足 D 约在 (225, 245)
    draw.line([(100, 320), (225, 245)], fill="gray", width=2)
    # 标注文字
    draw.text((80, 60), "C", fill="black")
    draw.text((75, 325), "A", fill="black")
    draw.text((510, 320), "B", fill="black")
    draw.text((235, 230), "D", fill="black")
    draw.text((250, 330), "c = 4", fill="black")
    draw.text((60, 200), "b = 3", fill="black")
    draw.text((320, 180), "a = 5", fill="black")
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def create_diagram_2() -> bytes:
    """图2：平行线与截线同位角、内错角"""
    im = Image.new("RGB", (600, 400), "white")
    draw = ImageDraw.Draw(im)
    # 平行线 l1, l2
    draw.line([(50, 120), (550, 120)], fill="black", width=3)
    draw.line([(50, 260), (550, 260)], fill="black", width=3)
    # 截线 l3
    draw.line([(150, 40), (450, 340)], fill="black", width=3)
    # 箭头与标注
    draw.text((560, 110), "l₁", fill="black")
    draw.text((560, 250), "l₂", fill="black")
    draw.text((460, 340), "l₃", fill="black")
    # 角弧度
    draw.arc([200, 100, 240, 140], start=45, end=180, fill="red", width=2)
    draw.text((245, 125), "∠1", fill="black")
    draw.arc([320, 240, 360, 280], start=45, end=180, fill="blue", width=2)
    draw.text((365, 265), "∠2", fill="black")
    draw.arc([290, 220, 330, 260], start=225, end=360, fill="green", width=2)
    draw.text((285, 230), "∠3", fill="black")
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def create_diagram_3() -> bytes:
    """图3：平面直角坐标系与一次函数 y = kx + b"""
    im = Image.new("RGB", (600, 400), "white")
    draw = ImageDraw.Draw(im)
    # X 轴与 Y 轴
    draw.line([(50, 200), (550, 200)], fill="black", width=2)
    draw.line([(300, 30), (300, 370)], fill="black", width=2)
    # 箭头
    draw.polygon([(550, 200), (540, 195), (540, 205)], fill="black")
    draw.polygon([(300, 30), (295, 40), (305, 40)], fill="black")
    draw.text((545, 210), "x", fill="black")
    draw.text((310, 30), "y", fill="black")
    draw.text((285, 205), "O", fill="black")
    # 直线 y = -0.8x + 60 -> 在图像坐标中穿过 (150, 80) 和 (450, 320)
    draw.line([(120, 60), (480, 340)], fill="#2563eb", width=3)
    # 交点标注
    draw.ellipse([296, 200 - 60 - 4, 304, 200 - 60 + 4], fill="red")
    draw.text((310, 135), "A(0, 2)", fill="black")
    draw.ellipse([300 + 75 - 4, 196, 300 + 75 + 4, 204], fill="red")
    draw.text((370, 210), "B(3, 0)", fill="black")
    draw.text((150, 70), "y = kx + 2", fill="#2563eb")
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def create_diagram_4() -> bytes:
    """图4：圆 O、内接三角形与弦长关系"""
    im = Image.new("RGB", (600, 400), "white")
    draw = ImageDraw.Draw(im)
    # 圆 O: 中心 (300, 200), 半径 130
    draw.ellipse([170, 70, 430, 330], outline="black", width=3)
    draw.ellipse([296, 196, 304, 204], fill="black")
    draw.text((310, 195), "O", fill="black")
    # 内接三角形 A(300, 70), B(190, 280), C(410, 280)
    draw.polygon([(300, 70), (190, 280), (410, 280)], outline="black", width=2)
    # 半径 OA, OB
    draw.line([(300, 200), (300, 70)], fill="gray", width=1)
    draw.line([(300, 200), (190, 280)], fill="gray", width=1)
    draw.text((295, 45), "A", fill="black")
    draw.text((170, 285), "B", fill="black")
    draw.text((420, 285), "C", fill="black")
    draw.text((235, 170), "r", fill="black")
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def create_diagram_5() -> bytes:
    """图5：平行四边形 ABCD 与高"""
    im = Image.new("RGB", (600, 400), "white")
    draw = ImageDraw.Draw(im)
    # A(150, 300), B(450, 300), C(520, 140), D(220, 140)
    draw.polygon([(150, 300), (450, 300), (520, 140), (220, 140)], outline="black", width=3)
    # 对角线 AC
    draw.line([(150, 300), (520, 140)], fill="#2563eb", width=2)
    # 垂线高 DE (220, 140) -> (220, 300)
    draw.line([(220, 140), (220, 300)], fill="gray", width=2)
    draw.rectangle([220, 280, 240, 300], outline="gray", width=1)
    draw.text((130, 305), "A", fill="black")
    draw.text((460, 305), "B", fill="black")
    draw.text((530, 130), "C", fill="black")
    draw.text((210, 120), "D", fill="black")
    draw.text((215, 310), "E", fill="black")
    draw.text((225, 210), "h", fill="black")
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def create_diagram_6() -> bytes:
    """图6：地理等高线地形图模型（山顶、鞍部、陡崖）"""
    im = Image.new("RGB", (600, 400), "white")
    draw = ImageDraw.Draw(im)
    # 山顶等高线 100m, 200m, 300m, 400m
    draw.ellipse([80, 80, 420, 320], outline="#16a34a", width=2)
    draw.text((90, 200), "100m", fill="#16a34a")
    draw.ellipse([130, 110, 370, 290], outline="#16a34a", width=2)
    draw.text((140, 200), "200m", fill="#16a34a")
    draw.ellipse([180, 140, 320, 260], outline="#16a34a", width=2)
    draw.text((190, 200), "300m", fill="#16a34a")
    draw.ellipse([230, 170, 270, 230], outline="#16a34a", width=2)
    draw.text((240, 190), "▲", fill="red")
    draw.text((245, 175), "甲(山顶)", fill="black")
    # 陡崖 (右侧等高线重合)
    draw.line([(420, 180), (450, 180)], fill="#d97706", width=4)
    draw.line([(420, 200), (460, 200)], fill="#d97706", width=4)
    draw.line([(420, 220), (450, 220)], fill="#d97706", width=4)
    draw.text((470, 195), "乙(陡崖)", fill="black")
    # 指向标
    draw.line([(530, 80), (530, 30)], fill="black", width=2)
    draw.polygon([(530, 25), (525, 35), (535, 35)], fill="black")
    draw.text((525, 10), "N", fill="black")
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


# 超长语文文言文/现代文阅读理解（超过 800 字，用于测试 is_oversized 启发式与自然跨页）
LONG_CHINESE_READING = (
    "【阅读理解与综合表达】阅读下面的文段，完成后续答题。\n\n"
    "自三峡七百里中，两岸连山，略无阙处。重岩叠嶂，隐天蔽日，自非亭午夜分，不见曦月。"
    "至于夏水襄陵，沿溯阻绝。或王命急宣，有时朝发白帝，暮到江陵，其间千二百里，虽乘奔御风，不以疾也。"
    "春冬之时，则素湍绿潭，回清倒影，绝巘多生怪柏，悬泉瀑布，飞漱其间，清荣峻茂，良多趣味。"
    "每至晴初霜旦，林寒涧肃，常有高猿长啸，属引凄异，空谷传响，哀转久绝。故渔者歌曰：‘巴东三峡巫峡长，猿鸣三声泪沾裳。’\n\n"
    "【拓展延伸阅读】我国古代文人墨客在游历大好河山之时，往往寄情于山水之间，抒发个人的胸襟抱负或失意感怀。"
    "北魏地理学家、散文家郦道元所著《水经注》，不仅是一部具有极高科学价值的古代地理学巨著，更以其笔墨精炼、语言生动的文学色彩，"
    "开创了我国古代游记散文的先河。在《三峡》一文中，作者以极其凝练优美的笔触，仅用一百五十余字，便将长江三峡奔放雄奇的山水神韵、"
    "四季变幻的景致特色描摹得淋漓尽致。夏水之迅疾、春冬之清幽、秋水之凄婉，无不令人拍案叫绝。\n\n"
    "思考与研读提示：文人笔下的山水，不仅是自然的造化，更是作者心境的投射。郦道元生活在南北朝时期，动荡的社会现实使得士大夫阶层"
    "渴望在宁静奇秀的自然山水中寻求精神的寄托与心灵的慰藉。我们在阅读这类古代写景散文时，不仅要体会其字斟句酌的语言艺术、动静结合的"
    "写景技巧，更应透过纸背，去感悟古人面对浩瀚自然时的敬畏之心与审美情怀。\n\n"
    "请结合文章内容，深入探究下列三个问题：\n"
    "（1）结合文中‘自非亭午夜分，不见曦月’一句，分析作者是如何正面描写与侧面烘托相结合来展现三峡群山特征的；\n"
    "（2）文中描写‘素湍绿潭，回清倒影’与‘悬泉瀑布，飞漱其间’分别运用了怎样的视角转换与色彩搭配手法？\n"
    "（3）请你以‘山水之美，美在心境’为主题，撰写一段不少于 150 字的心得体会，谈谈你对古人寄情山水传统美学的现代理解。"
)


def seed_m4_data():
    db = SessionLocal()
    try:
        # 1. 确保默认学生
        student = db.query(Student).filter(Student.id == 1).first()
        if not student:
            student = Student(id=1, name="初一同学", grade="初一")
            db.add(student)
            db.commit()

        # 2. 获取初一 7 科科目映射
        subjects = db.query(Subject).all()
        sub_map = {s.name: s.id for s in subjects}
        print(f"Loaded {len(sub_map)} subjects: {list(sub_map.keys())}")

        # 3. 生成 6 张高分辨率几何插图并通过 save_image_bytes 保存
        print("Generating 6 geometric diagrams...")
        diagram_generators = [
            ("geo_triangle.jpg", create_diagram_1),
            ("geo_parallel.jpg", create_diagram_2),
            ("geo_coordinates.jpg", create_diagram_3),
            ("geo_circle.jpg", create_diagram_4),
            ("geo_parallelogram.jpg", create_diagram_5),
            ("geo_contour.jpg", create_diagram_6),
        ]
        saved_diagrams = []
        for filename, gen_fn in diagram_generators:
            img_bytes = gen_fn()
            sha, rel_orig, rel_thumb = save_image_bytes(img_bytes, filename)
            saved_diagrams.append((rel_orig, rel_thumb))
            print(f"  Saved {filename} -> {rel_orig}")

        # 4. 清理既有 demo 数据，保证幂等执行
        db.query(MistakeRecord).filter(MistakeRecord.source_reference.like("M4_DEMO_%")).delete(synchronize_session=False)
        db.query(Paper).filter(Paper.title == "初一错题周末重练示范卷").delete(synchronize_session=False)
        db.commit()

        # 5. 组装 25 道典型初一错题（7 科全覆盖，6 道带几何图，1 道超长语文）
        today = date.today()
        created_now = datetime.now()

        questions_def = [
            # 数学 7 题 (前 4 题带图)
            {
                "subject": "数学",
                "source_ref": "M4_DEMO_MATH_01",
                "error_type": "概念模糊",
                "extracted_text": "如图，在 Rt△ABC 中，∠A = 90°，AC = 3，AB = 4。若从点 A 向斜边 BC 作垂线 AD，垂足为 D，求垂线段 AD 的长及 △ACD 的面积。",
                "img_idx": 0,
                "mastery_status": "未掌握",
                "review_count": 0,
                "next_review_date": today,
            },
            {
                "subject": "数学",
                "source_ref": "M4_DEMO_MATH_02",
                "error_type": "思路卡壳",
                "extracted_text": "如图，已知直线 l₁ ∥ l₂，截线 l₃ 分别交 l₁、l₂ 于点 A、B。若 ∠1 = 125°，且 ∠3 与 ∠2 互为对顶角，求 ∠2 和 ∠3 的度数，并说明理由。",
                "img_idx": 1,
                "mastery_status": "未掌握",
                "review_count": 1,
                "next_review_date": today,
            },
            {
                "subject": "数学",
                "source_ref": "M4_DEMO_MATH_03",
                "error_type": "计算错误",
                "extracted_text": "如图，平面直角坐标系中一次函数 y = kx + 2 的图象经过点 B(3, 0)，与 y 轴交于点 A。求：（1）常数 k 的值；（2）△AOB 的面积；（3）当 x 满足什么条件时，y > 0？",
                "img_idx": 2,
                "mastery_status": "未掌握",
                "review_count": 0,
                "next_review_date": today,
            },
            {
                "subject": "数学",
                "source_ref": "M4_DEMO_MATH_04",
                "error_type": "粗心大意",
                "extracted_text": "如图，⊙O 是等腰 △ABC 的外接圆，AB = AC，圆心 O 到弦 BC 的距离为 3cm。已知 ⊙O 的半径 r = 5cm，求底边 BC 的长及 △ABC 的面积。",
                "img_idx": 3,
                "mastery_status": "未掌握",
                "review_count": 2,
                "next_review_date": today - timedelta(days=1),
            },
            {
                "subject": "数学",
                "source_ref": "M4_DEMO_MATH_05",
                "error_type": "思路卡壳",
                "extracted_text": "如图，在平行四边形 ABCD 中，对角线 AC 分别交高 DE 于点 E。已知 AB = 10，高 DE = 6，求平行四边形 ABCD 的周长及 △ABC 的面积。",
                "img_idx": 4,
                "mastery_status": "未掌握",
                "review_count": 0,
                "next_review_date": today,
            },
            {
                "subject": "数学",
                "source_ref": "M4_DEMO_MATH_06",
                "error_type": "计算错误",
                "extracted_text": "解一元一次不等式组：\n2x - 1 < 3x + 2\n(x + 1)/2 ≥ (2x - 1)/3\n并在数轴上表示出该不等式组的解集，写出该不等式组的所有非负整数解。",
                "img_idx": None,
                "mastery_status": "未掌握",
                "review_count": 0,
                "next_review_date": today,
            },
            {
                "subject": "数学",
                "source_ref": "M4_DEMO_MATH_07",
                "error_type": "概念模糊",
                "extracted_text": "已知关于 x 的方程 (2m - 1)x² + 3x - 5 = 0 是一元一次方程，求代数式 (m - 2)²⁰²⁴ 的值，并检验 x = 1 是否为该方程的解。",
                "img_idx": None,
                "mastery_status": "未掌握",
                "review_count": 1,
                "next_review_date": today,
            },

            # 语文 4 题 (含 1 道超长文本)
            {
                "subject": "语文",
                "source_ref": "M4_DEMO_CHI_01",
                "error_type": "思路卡壳",
                "extracted_text": LONG_CHINESE_READING,
                "img_idx": None,
                "mastery_status": "未掌握",
                "review_count": 0,
                "next_review_date": today,
            },
            {
                "subject": "语文",
                "source_ref": "M4_DEMO_CHI_02",
                "error_type": "概念模糊",
                "extracted_text": "古诗文名句默写与理解：\n（1）《论语》中阐述学与思辩证关系的句子是：‘____________________，____________________。’\n（2）曹操《观沧海》中借日月星辰展现博大胸襟的诗句是：‘____________________，若出其中；____________________，若出其里。’",
                "img_idx": None,
                "mastery_status": "未掌握",
                "review_count": 0,
                "next_review_date": today,
            },
            {
                "subject": "语文",
                "source_ref": "M4_DEMO_CHI_03",
                "error_type": "粗心大意",
                "extracted_text": "下列各句中加点成语使用恰当的一项是（   ）\nA. 这篇作文构思巧妙，行文行云流水，老师看后不由得叹为观止。\nB. 他在台上演讲得绘声绘色，台下听众个个面面相觑，报以热烈的掌声。\nC. 遇到困难时，我们不能妄自菲薄，而应该坚定信心，迎难而上。\nD. 这座新建的图书馆宏伟壮观，藏书丰富，真是巧夺天工。",
                "img_idx": None,
                "mastery_status": "待复习",
                "review_count": 2,
                "next_review_date": today - timedelta(days=1),
            },
            {
                "subject": "语文",
                "source_ref": "M4_DEMO_CHI_04",
                "error_type": "思路卡壳",
                "extracted_text": "请分析老舍《济南的冬天》中‘一个老城，有山有水，全在天底下晒着阳光，暖和安适地睡着，只等春风来把它们唤醒’一句的修辞手法及表达效果。",
                "img_idx": None,
                "mastery_status": "未掌握",
                "review_count": 0,
                "next_review_date": today,
            },

            # 英语 4 题
            {
                "subject": "英语",
                "source_ref": "M4_DEMO_ENG_01",
                "error_type": "概念模糊",
                "extracted_text": "Complete the sentences with the correct form of the verbs in brackets:\n(1) Listen! The birds ____________ (sing) sweetly in the tall tree.\n(2) My father usually ____________ (go) to work by underground every morning.\n(3) Look! They ____________ (not play) basketball on the playground now.",
                "img_idx": None,
                "mastery_status": "未掌握",
                "review_count": 0,
                "next_review_date": today,
            },
            {
                "subject": "英语",
                "source_ref": "M4_DEMO_ENG_02",
                "error_type": "粗心大意",
                "extracted_text": "Choose the best answer for each blank:\n— Can I speak to Mary, please?\n— Hold on, please. She ____________ the piano in the music room.\n(A) plays   (B) is playing   (C) played   (D) will play",
                "img_idx": None,
                "mastery_status": "未掌握",
                "review_count": 1,
                "next_review_date": today,
            },
            {
                "subject": "英语",
                "source_ref": "M4_DEMO_ENG_03",
                "error_type": "思路卡壳",
                "extracted_text": "Reading Comprehension:\nRead the passage about healthy living habits and answer the questions:\n(1) Why is having breakfast every day important for teenagers?\n(2) How much sleep does a junior high school student need each night?\n(3) What advice does the author give on managing screen time?",
                "img_idx": None,
                "mastery_status": "未掌握",
                "review_count": 0,
                "next_review_date": today,
            },
            {
                "subject": "英语",
                "source_ref": "M4_DEMO_ENG_04",
                "error_type": "概念模糊",
                "extracted_text": "Rewrite the following sentences as required:\n(1) There are some apples on the table. (改为否定句)\n    ________________________________________________________\n(2) She likes playing the violin because it's relaxing. (对划线部分提问)\n    ________________________________________________________",
                "img_idx": None,
                "mastery_status": "待复习",
                "review_count": 2,
                "next_review_date": today - timedelta(days=2),
            },

            # 道德与法治 3 题
            {
                "subject": "道德与法治",
                "source_ref": "M4_DEMO_MOR_01",
                "error_type": "概念模糊",
                "extracted_text": "材料分析题：\n某初中开展‘做更好的自己’主题班会。小明同学说：‘我数学成绩很好，但我性格内向，不善于表达，我觉得自己很失败。’\n请运用所学知识回答：\n（1）小明应如何正确接纳与欣赏自己？\n（2）请你为小明提出两条如何做更好的自己的具体建议。",
                "img_idx": None,
                "mastery_status": "未掌握",
                "review_count": 0,
                "next_review_date": today,
            },
            {
                "subject": "道德与法治",
                "source_ref": "M4_DEMO_MOR_02",
                "error_type": "粗心大意",
                "extracted_text": "辨析题：‘遵守社会规则会限制我们的自由，因此追求真正的自由就不应受到规则的约束。’请运用‘自由与规则’的关系对此观点进行简要评析。",
                "img_idx": None,
                "mastery_status": "未掌握",
                "review_count": 1,
                "next_review_date": today,
            },
            {
                "subject": "道德与法治",
                "source_ref": "M4_DEMO_MOR_03",
                "error_type": "概念模糊",
                "extracted_text": "友谊的特质是什么？结合初中生活实际，简述我们应如何澄清对友谊的片面认识，呵护珍贵友谊？",
                "img_idx": None,
                "mastery_status": "待复习",
                "review_count": 2,
                "next_review_date": today - timedelta(days=1),
            },

            # 历史 3 题
            {
                "subject": "历史",
                "source_ref": "M4_DEMO_HIS_01",
                "error_type": "思路卡壳",
                "extracted_text": "材料简答题：\n‘宗室非有军功论，不得为属籍。明尊卑爵秩等级，各以差次名田宅，臣妾衣服以家次。有功者显荣，无功者虽富无所芬华。’\n——《史记·商君列传》\n（1）上述材料反映了商鞅变法中的哪一项具体措施？\n（2）该项措施对当时秦国的社会阶层与军队战斗力产生了怎样的重大影响？",
                "img_idx": None,
                "mastery_status": "未掌握",
                "review_count": 0,
                "next_review_date": today,
            },
            {
                "subject": "历史",
                "source_ref": "M4_DEMO_HIS_02",
                "error_type": "概念模糊",
                "extracted_text": "简述秦始皇巩固中央集权统治所采取的经济与文化措施，并分析‘统一度量衡’与‘统一文字’对中华多民族国家发展的历史意义。",
                "img_idx": None,
                "mastery_status": "未掌握",
                "review_count": 1,
                "next_review_date": today,
            },
            {
                "subject": "历史",
                "source_ref": "M4_DEMO_HIS_03",
                "error_type": "粗心大意",
                "extracted_text": "汉武帝采纳董仲舒的建议‘罢黜百家，独尊儒术’，其根本目的是什么？汉武帝时期在思想上和教育上分别采取了哪些具体推行儒学举措？",
                "img_idx": None,
                "mastery_status": "待复习",
                "review_count": 2,
                "next_review_date": today - timedelta(days=2),
            },

            # 地理 2 题 (第 1 题带图)
            {
                "subject": "地理",
                "source_ref": "M4_DEMO_GEO_01",
                "error_type": "概念模糊",
                "extracted_text": "读某地区等高线地形图，回答下列问题：\n（1）图中甲处代表的地形部位是__________，乙处代表的地形部位是__________；\n（2）若甲处的海拔约为 480 米，乙处最高海拔为 200 米，求两地的相对高度；\n（3）图中的指向标指示什么方向？若从山脚沿虚线攀登至甲山顶，哪一坡段坡度较陡？请说明判断依据。",
                "img_idx": 5,
                "mastery_status": "未掌握",
                "review_count": 0,
                "next_review_date": today,
            },
            {
                "subject": "地理",
                "source_ref": "M4_DEMO_GEO_02",
                "error_type": "思路卡壳",
                "extracted_text": "简述地球公转产生的地理现象（至少列举三项），并说明春分日（3月21日前后）太阳直射点纬度位置以及全球昼夜长短分布特征。",
                "img_idx": None,
                "mastery_status": "未掌握",
                "review_count": 1,
                "next_review_date": today,
            },

            # 生物 2 题
            {
                "subject": "生物",
                "source_ref": "M4_DEMO_BIO_01",
                "error_type": "概念模糊",
                "extracted_text": "动植物细胞结构对比辨析：\n（1）植物细胞特有而动物细胞没有的细胞结构有哪些？（列举三种）\n（2）细胞中的‘能量转换器’包括哪两项？哪一项被称为细胞的‘动力工厂’？",
                "img_idx": None,
                "mastery_status": "未掌握",
                "review_count": 0,
                "next_review_date": today,
            },
            {
                "subject": "生物",
                "source_ref": "M4_DEMO_BIO_02",
                "error_type": "思路卡壳",
                "extracted_text": "实验探究：在‘绿叶在光下制造有机物’的实验中：\n（1）把盆栽天竺葵放在黑暗处一昼夜的目的是什么？\n（2）用黑纸片把叶片的一部分遮盖起来，该处理的目的是设置__________；\n（3）经脱色、漂洗并滴加碘液后，叶片见光部分呈现什么颜色？证明了什么？",
                "img_idx": None,
                "mastery_status": "未掌握",
                "review_count": 0,
                "next_review_date": today,
            },
        ]

        inserted_records = []
        for q in questions_def:
            sub_id = sub_map.get(q["subject"])
            if not sub_id:
                print(f"Warning: Subject {q['subject']} not found in db, skipping")
                continue

            orig_path = None
            thumb_path = None
            if q["img_idx"] is not None and q["img_idx"] < len(saved_diagrams):
                orig_path, thumb_path = saved_diagrams[q["img_idx"]]

            rec = MistakeRecord(
                student_id=student.id,
                subject_id=sub_id,
                source_type="homework",
                source_reference=q["source_ref"],
                original_image_path=orig_path,
                thumbnail_path=thumb_path,
                extracted_text=q["extracted_text"],
                error_type=q["error_type"],
                mastery_status=q["mastery_status"],
                review_count=q["review_count"],
                next_review_date=q["next_review_date"],
                created_at=created_now,
            )
            db.add(rec)
            inserted_records.append(rec)

        db.commit()
        for r in inserted_records:
            db.refresh(r)

        print(f"Successfully seeded {len(inserted_records)} Junior 1 questions.")

        # 6. 生成一张包含前 20 题的标准 demo 试卷（含全部 6 张几何插图与 1 道超长题）
        from backend.app.routers.paper import _check_oversized, CORE_7_SUBJECTS
        demo_records = sorted(
            inserted_records[:20],
            key=lambda r: (r.subject.sort_order if (r.subject and r.subject.name in CORE_7_SUBJECTS) else 999, r.id)
        )
        demo_mid_list = [r.id for r in demo_records]
        img_q_count = sum(1 for r in demo_records if r.original_image_path)
        est_pages = max(1, round(len(demo_mid_list) / 4) + math.ceil(img_q_count / 6))

        # 动态计算超长题预警，避免硬编码错位
        dynamic_warnings = []
        for idx, r in enumerate(demo_records):
            has_img = bool(r.original_image_path or r.thumbnail_path)
            if _check_oversized(r.extracted_text, "standard", has_image=has_img):
                dynamic_warnings.append(f"第 {idx + 1} 题题干内容较长，可能跨页显示")

        demo_paper = Paper(
            title="初一错题周末重练示范卷",
            subtitle="满分: 100分 · 建议用时: 45分钟",
            mistake_ids=json.dumps(demo_mid_list),
            sort_by="subject",
            space_level="standard",
            style_mode="grid",
            show_error_type=False,
            estimated_pages=est_pages,
            warnings=json.dumps(dynamic_warnings, ensure_ascii=False),
            student_name=student.name,
            status="draft",
        )
        db.add(demo_paper)
        db.commit()
        db.refresh(demo_paper)
        print(f"Successfully created demo paper id={demo_paper.id} with {len(demo_mid_list)} questions, estimated_pages={est_pages}, warnings={dynamic_warnings}")


    finally:
        db.close()


if __name__ == "__main__":
    seed_m4_data()
