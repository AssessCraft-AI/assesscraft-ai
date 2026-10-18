import html
import io
import csv
import xml.etree.ElementTree as ET
from xml.dom import minidom
from xml.sax.saxutils import escape
from typing import List, Dict, Any, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
)
from reportlab.pdfgen import canvas


SECTION_TITLES = {
    "mcq": "MULTIPLE CHOICE QUESTIONS",
    "short_answer": "STRUCTURED SHORT ANSWER QUESTIONS",
    "essay": "FREE RESPONSE (ESSAY) QUESTIONS",
}
SECTION_NAMES = {"mcq": "Multiple Choice", "short_answer": "Structured Short Answer", "essay": "Free Response"}


def _sections(items: List[Dict[str, Any]]) -> List[tuple]:
    """Groups items by type in paper order, skipping empty types: [(qType, items, first question number)]."""
    out, n = [], 1
    for qt in SECTION_TITLES:
        group = [it for it in items if it.get("qType", "mcq") == qt]
        if group:
            out.append((qt, group, n))
            n += len(group)
    return out


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and render total page count and footer."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_footer(num_pages)
            super().showPage()
        super().save()

    def draw_footer(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        # Header rule & text
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(40, 40, 555, 40)
        self.drawString(
            40,
            28,
            "AssessCraft AI — Academic Quality Assurance & Assessment Copilot | Confidential Examination Material",
        )
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(555, 28, page_str)
        self.restoreState()


def render_exam_pdf(
    assessment: Dict[str, Any],
    version_label: str,
    items: List[Dict[str, Any]],
    course: Optional[Dict[str, Any]] = None,
) -> bytes:
    """
    Renders an official, print-ready examination paper PDF using ReportLab.
    Includes university header, candidate instructions, academic integrity pledge,
    and distinct MCQ and structured short-answer sections.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=55,
    )

    styles = getSampleStyleSheet()

    # Custom typography
    inst_title_style = ParagraphStyle(
        "InstTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        alignment=1,  # Center
        textColor=colors.HexColor("#0F172A"),
    )
    dept_style = ParagraphStyle(
        "DeptTitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=12,
        alignment=1,
        textColor=colors.HexColor("#475569"),
    )
    paper_title_style = ParagraphStyle(
        "PaperTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        alignment=1,
        textColor=colors.HexColor("#1E3A8A"),
    )
    version_banner_style = ParagraphStyle(
        "VersionBanner",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        alignment=1,
        textColor=colors.HexColor("#0284C7"),
    )
    meta_style = ParagraphStyle(
        "MetaText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#334155"),
    )
    meta_bold = ParagraphStyle(
        "MetaBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#0F172A"),
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=10,
        spaceAfter=6,
    )
    question_stem = ParagraphStyle(
        "QuestionStem",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#0F172A"),
    )
    question_header = ParagraphStyle(
        "QuestionHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#1E293B"),
    )
    option_style = ParagraphStyle(
        "OptionStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12.5,
        textColor=colors.HexColor("#334155"),
    )
    instruction_style = ParagraphStyle(
        "InstructionStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#334155"),
    )

    story = []

    course_code = course.get("code", "CS2040") if course else "CS2040"
    course_name = course.get("title", "Database Systems") if course else "Database Systems"
    total_marks = assessment.get("totalMarks", 100)
    duration_mins = assessment.get("durationMins", 120)
    is_approved = assessment.get("status") == "approved"
    status_label = "OFFICIAL EXAMINATION PAPER — ACCREDITED" if is_approved else "CONFIDENTIAL DRAFT — NOT FOR DISTRIBUTION"
    status_color = "#15803D" if is_approved else "#DC2626"

    # 1. Institutional Header
    story.append(Paragraph("NATIONAL UNIVERSITY EXAMINATION BOARD", inst_title_style))
    story.append(Spacer(1, 2))
    story.append(Paragraph("FACULTY OF COMPUTING & INFORMATION SYSTEMS", dept_style))
    story.append(Spacer(1, 6))
    story.append(Paragraph(escape(f"{course_code}: {course_name.upper()}"), paper_title_style))
    story.append(Spacer(1, 3))
    sitting_name = "MAIN SITTING" if version_label == "A" else "REPEAT / SUPPLEMENTARY SITTING"
    story.append(Paragraph(f"EXAMINATION PAPER — VERSION {version_label} ({sitting_name})", version_banner_style))
    story.append(Spacer(1, 6))

    # Watermark / Status Bar
    status_table = Table(
        [[Paragraph(f"<font color='{status_color}'><b>{status_label}</b></font>", dept_style)]],
        colWidths=[515],
    )
    status_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor(status_color)),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(status_table)
    story.append(Spacer(1, 8))

    # Metadata Grid
    meta_data = [
        [
            Paragraph("<b>Time Allowed:</b>", meta_bold),
            Paragraph(f"{duration_mins // 60} Hours ({duration_mins} Minutes)", meta_style),
            Paragraph("<b>Total Marks:</b>", meta_bold),
            Paragraph(f"{total_marks} Marks", meta_style),
        ],
        [
            Paragraph("<b>Total Questions:</b>", meta_bold),
            Paragraph(f"{len(items)} Questions", meta_style),
            Paragraph("<b>Permitted Materials:</b>", meta_bold),
            Paragraph("None (Closed Book)", meta_style),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[95, 160, 95, 165])
    meta_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # Instructions Box
    sections = _sections(items)
    suggested = {t.get("qType"): t.get("timeMins", 0) for t in assessment.get("typeConfig") or []}
    qts = {qt for qt, _, _ in sections}
    section_list = ", ".join(f"Section {n} ({SECTION_NAMES[qt]})" for n, (qt, _, _) in enumerate(sections, start=1))
    inst_lines = [
        f"This paper consists of <b>{len(sections)} SECTION{'S' if len(sections) != 1 else ''}</b>: {section_list}.",
        "Answer <b>ALL</b> questions in every section.",
    ]
    if "mcq" in qts:
        inst_lines.append("For multiple choice questions, choose the <b>single best answer</b> (A, B, C, or D) and record it on the provided answer sheet.")
    if "short_answer" in qts:
        inst_lines.append("For structured questions, write concise, legible answers and show working where required.")
    if "essay" in qts:
        inst_lines.append("For free response questions, write well-organised extended answers with justified arguments.")
    inst_lines.append("<i>Honor Pledge: By commencing this exam, you certify that all submitted work is solely your own.</i>")
    instructions = [Paragraph("<b>INSTRUCTIONS TO CANDIDATES:</b>", meta_bold)] + [
        Paragraph(f"{n}. {line}", instruction_style) for n, line in enumerate(inst_lines, start=1)
    ]
    inst_table = Table([[Paragraph("<br/>".join([p.text for p in instructions]), instruction_style)]], colWidths=[515])
    inst_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF9C3")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#FACC15")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ])
    )
    story.append(inst_table)
    story.append(Spacer(1, 12))

    for sec_no, (qt, group, first_no) in enumerate(sections, start=1):
        sec_marks = sum(it.get("marks", 1) for it in group)
        time_note = f" — suggested {suggested[qt]} mins" if suggested.get(qt) else ""
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0F172A"), spaceBefore=4 if sec_no == 1 else 8, spaceAfter=4))
        story.append(Paragraph(f"SECTION {sec_no}: {SECTION_TITLES[qt]} [{sec_marks} MARKS]{time_note}", section_heading))
        if qt == "mcq":
            story.append(Paragraph("<i>Answer all questions. Each question is worth the marks indicated. Select the single best answer.</i>", instruction_style))
            story.append(Spacer(1, 6))
            for idx, item in enumerate(group, start=first_no):
                q_elements = []
                marks = item.get("marks", 1)
                clo = item.get("cloId", "")
                bloom = item.get("bloom", "").capitalize()
                header_text = f"Question {idx} [{marks} Mark{'s' if marks > 1 else ''}] <font color='#64748B'>({clo} • {bloom})</font>"
                q_elements.append(Paragraph(header_text, question_header))
                q_elements.append(Spacer(1, 2))
                q_elements.append(Paragraph(escape(item.get("stem", "")), question_stem))
                q_elements.append(Spacer(1, 4))

                options = item.get("options") or []
                opt_rows = []
                for opt in options:
                    opt_id = opt.get("id", "")
                    opt_text = opt.get("text", "")
                    opt_rows.append([
                        Paragraph(f"<b>[{opt_id}]</b>", meta_bold),
                        Paragraph(escape(opt_text), option_style),
                    ])
                if opt_rows:
                    opt_table = Table(opt_rows, colWidths=[24, 480])
                    opt_table.setStyle(
                        TableStyle([
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("TOPPADDING", (0, 0), (-1, -1), 1),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                            ("LEFTPADDING", (0, 0), (-1, -1), 0),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ])
                    )
                    q_elements.append(opt_table)

                q_elements.append(Spacer(1, 8))
                story.append(KeepTogether(q_elements))
        else:
            story.append(Paragraph("<i>Answer all questions. Show clear working and analytical justifications.</i>", instruction_style))
            story.append(Spacer(1, 6))

            for idx, item in enumerate(group, start=first_no):
                q_elements = []
                marks = item.get("marks", 8)
                clo = item.get("cloId", "")
                bloom = item.get("bloom", "").capitalize()
                topic = item.get("topicId", "Core Curriculum")
                header_text = f"Question {idx} [{marks} Marks] <font color='#64748B'>({clo} • {topic} • {bloom})</font>"
                q_elements.append(Paragraph(header_text, question_header))
                q_elements.append(Spacer(1, 2))
                q_elements.append(Paragraph(escape(item.get("stem", "")), question_stem))
                q_elements.append(Spacer(1, 6))

                # Blank response space box
                box = Table([[Paragraph("<font color='#94A3B8'><i>[Candidate Response Area — Show working clearly]</i></font>", instruction_style)]], colWidths=[515], rowHeights=[120 if qt == "essay" else 45])
                box.setStyle(
                    TableStyle([
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFAFA")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ])
                )
                q_elements.append(box)
                q_elements.append(Spacer(1, 10))
                story.append(KeepTogether(q_elements))

    # Build document with NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer.getvalue()


def render_marking_guide_pdf(
    assessment: Dict[str, Any],
    version_label: str,
    items: List[Dict[str, Any]],
    course: Optional[Dict[str, Any]] = None,
) -> bytes:
    """
    Renders an official, confidential Lecturer's Marking Guide & Model Solutions PDF.
    Contains MCQ answer keys with pedagogical distractor rationales, and structured
    short-answer model solutions with explicit point allocation rubrics.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=55,
    )

    styles = getSampleStyleSheet()

    guide_title = ParagraphStyle(
        "GuideTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        alignment=1,
        textColor=colors.HexColor("#991B1B"),
    )
    sub_title = ParagraphStyle(
        "GuideSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        alignment=1,
        textColor=colors.HexColor("#475569"),
    )
    section_head = ParagraphStyle(
        "GuideSecHead",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=10,
        spaceAfter=6,
    )
    q_title = ParagraphStyle(
        "GuideQTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#1E293B"),
    )
    body_text = ParagraphStyle(
        "GuideBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#1E293B"),
    )
    table_head = ParagraphStyle(
        "TableHead",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#FFFFFF"),
    )

    story = []

    course_code = course.get("code", "CS2040") if course else "CS2040"
    course_name = course.get("title", "Database Systems") if course else "Database Systems"

    story.append(Paragraph("CONFIDENTIAL LECTURER'S MARKING GUIDE & DETAILED RUBRIC", guide_title))
    story.append(Spacer(1, 3))
    story.append(Paragraph(escape(f"{course_code}: {course_name}") + f" — VERSION {version_label}", sub_title))
    story.append(Spacer(1, 8))

    # Notice Box
    notice = Table([[Paragraph("<b>RESTRICTED DOCUMENT:</b> For authorized academic examiners and external moderators only. Do not disclose before post-examination grading board.", body_text)]], colWidths=[515])
    notice.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEE2E2")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#EF4444")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(notice)
    story.append(Spacer(1, 10))

    for sec_no, (qt, group, first_no) in enumerate(_sections(items), start=1):
        if qt == "mcq":
            story.append(Paragraph(f"SECTION {sec_no}: MULTIPLE CHOICE ANSWER KEYS", section_head))
            key_rows = [[
                Paragraph("Q#", table_head),
                Paragraph("Key", table_head),
                Paragraph("Marks", table_head),
                Paragraph("CLO / Bloom", table_head),
                Paragraph("Pedagogical Distractor Rationale / Explanation", table_head),
            ]]
            for idx, item in enumerate(group, start=first_no):
                key = item.get("key", "A")
                marks = item.get("marks", 1)
                clo = item.get("cloId", "CLO1")
                bloom = item.get("bloom", "understand").capitalize()
                rationale = item.get("rationale") or item.get("distractorRationales") or "Author validated key."
                if isinstance(rationale, dict):
                    rationale_str = escape("; ".join([f"{k}: {v}" for k, v in rationale.items()]))
                else:
                    rationale_str = escape(str(rationale))

                key_rows.append([
                    Paragraph(f"Q{idx}", body_text),
                    Paragraph(f"<b>[{escape(str(key))}]</b>", body_text),
                    Paragraph(str(marks), body_text),
                    Paragraph(f"{clo}<br/>{bloom}", body_text),
                    Paragraph(rationale_str, body_text),
                ])

            key_table = Table(key_rows, colWidths=[28, 35, 38, 70, 344])
            key_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ]))
            story.append(key_table)
            story.append(Spacer(1, 14))
            continue

        story.append(Paragraph(f"SECTION {sec_no}: {SECTION_TITLES[qt]} — MODEL ANSWERS & RUBRICS", section_head))
        for idx, item in enumerate(group, start=first_no):
            q_elem = []
            marks = item.get("marks", 8)
            clo = item.get("cloId", "")
            topic = item.get("topicId", "")
            q_elem.append(Paragraph(f"Question {idx} [{marks} Marks] — {clo} ({topic})", q_title))
            q_elem.append(Spacer(1, 2))

            key_text = escape(str(item.get("key", "Standard academic solution.")))
            rubric_text = item.get("rubric") or item.get("rationale") or "Award full marks for complete solution."
            if isinstance(rubric_text, dict):
                rubric_str = "<br/>".join([f"• <b>{escape(str(k))}:</b> {escape(str(v))}" for k, v in rubric_text.items()])
            else:
                rubric_str = escape(str(rubric_text))

            citations = item.get("sourceCitations") or []
            cite_str = ""
            if citations:
                c0 = citations[0]
                cite_str = f"<br/><font color='#64748B'><b>Source Grounding:</b> {escape(c0.get('snippet', '')[:120])}...</font>"

            content_html = (
                f"<b>Model Solution / Expected Answer:</b><br/>{key_text}<br/><br/>"
                f"<b>Marking Scheme & Point Allocations:</b><br/>{rubric_str}"
                f"{cite_str}"
            )
            rubric_box = Table([[Paragraph(content_html, body_text)]], colWidths=[515])
            rubric_box.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]))
            q_elem.append(rubric_box)
            q_elem.append(Spacer(1, 8))
            story.append(KeepTogether(q_elem))

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer.getvalue()


def render_moodle_xml(
    assessment: Dict[str, Any],
    version_label: str,
    items: List[Dict[str, Any]],
    course: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Renders valid Moodle XML format (<quiz>) containing multichoice and essay/shortanswer
    questions with fractional scores, answer rationales, and tags for automated LMS import.
    """
    course_code = course.get("code", "CS2040") if course else "CS2040"
    assessment_title = assessment.get("title", f"{course_code} Examination")

    quiz = ET.Element("quiz")

    # Category header
    cat_q = ET.SubElement(quiz, "question", type="category")
    cat = ET.SubElement(cat_q, "category")
    cat_text = ET.SubElement(cat, "text")
    cat_text.text = f"$course$/{assessment_title} - Version {version_label}"

    for idx, item in enumerate(items, start=1):
        q_type = item.get("qType", "mcq")
        marks = item.get("marks", 1)
        clo = item.get("cloId", "CLO1")
        bloom = item.get("bloom", "understand")

        if q_type == "mcq":
            q = ET.SubElement(quiz, "question", type="multichoice")
            name = ET.SubElement(q, "name")
            ET.SubElement(name, "text").text = f"Q{idx:02d}_{item.get('topicId', 'General')}_{clo}"

            q_text = ET.SubElement(q, "questiontext", format="html")
            ET.SubElement(q_text, "text").text = f"<p>{html.escape(item.get('stem', ''))}</p>"

            ET.SubElement(q, "defaultgrade").text = str(marks)
            ET.SubElement(q, "penalty").text = "0.3333333"
            ET.SubElement(q, "hidden").text = "0"
            ET.SubElement(q, "single").text = "true"
            ET.SubElement(q, "shuffleanswers").text = "1"
            ET.SubElement(q, "answernumbering").text = "abc"

            correct_key = item.get("key", "A")
            rationales = item.get("distractorRationales") or {}

            options = item.get("options") or []
            for opt in options:
                opt_id = opt.get("id", "")
                is_correct = opt_id == correct_key
                fraction = "100" if is_correct else "0"
                ans = ET.SubElement(q, "answer", fraction=fraction, format="html")
                ET.SubElement(ans, "text").text = f"<p>{html.escape(opt.get('text', ''))}</p>"

                feedback = ET.SubElement(ans, "feedback", format="html")
                fb_text = rationales.get(opt_id) if isinstance(rationales, dict) else ""
                if not fb_text:
                    fb_text = "Correct answer." if is_correct else "Incorrect choice."
                ET.SubElement(feedback, "text").text = f"<p>{html.escape(str(fb_text))}</p>"

        else:
            # Short answer / Essay
            q = ET.SubElement(quiz, "question", type="essay")
            name = ET.SubElement(q, "name")
            ET.SubElement(name, "text").text = f"Q{idx:02d}_{item.get('topicId', 'General')}_{clo}"

            q_text = ET.SubElement(q, "questiontext", format="html")
            ET.SubElement(q_text, "text").text = f"<p>{html.escape(item.get('stem', ''))}</p>"

            ET.SubElement(q, "defaultgrade").text = str(marks)
            ET.SubElement(q, "responseformat").text = "editor"
            ET.SubElement(q, "responserequired").text = "1"
            ET.SubElement(q, "responsefieldlines").text = "10"

            graderinfo = ET.SubElement(q, "graderinfo", format="html")
            rubric = item.get("rubric") or item.get("rationale") or "Consult model answer."
            rubric_str = str(rubric)
            model_ans = item.get("key", "Standard academic solution.")
            graderinfo_text = f"<h3>Marking Rubric:</h3><p>{html.escape(rubric_str)}</p><h3>Model Answer:</h3><p>{html.escape(str(model_ans))}</p>"
            ET.SubElement(graderinfo, "text").text = graderinfo_text

        # Tags
        tags = ET.SubElement(q, "tags")
        tag_clo = ET.SubElement(tags, "tag")
        ET.SubElement(tag_clo, "text").text = clo
        tag_bloom = ET.SubElement(tags, "tag")
        ET.SubElement(tag_bloom, "text").text = bloom

    # Format XML nicely
    raw_xml = ET.tostring(quiz, encoding="utf-8")
    parsed = minidom.parseString(raw_xml)
    return parsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")


def render_clo_matrix_csv(
    assessment: Dict[str, Any],
    version_label: str,
    items: List[Dict[str, Any]],
    course: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Renders a comprehensive CSV matrix documenting item-level CLO, Bloom taxonomy,
    topic, difficulty, and source citations for educational governance and QA audit.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Headers
    writer.writerow([
        "Question Number",
        "Item ID",
        "Version",
        "Question Type",
        "Marks",
        "Course Learning Outcome (CLO)",
        "Topic",
        "Bloom Taxonomy Level",
        "Estimated Difficulty (1-5)",
        "Correct Answer / Key",
        "Stem Excerpt",
        "Source Citation Document",
        "Source Citation Snippet",
    ])

    for idx, item in enumerate(items, start=1):
        q_type = SECTION_NAMES.get(item.get("qType", "mcq"), "Structured Short Answer")
        stem = item.get("stem", "").replace("\n", " ")
        stem_excerpt = stem[:120] + ("..." if len(stem) > 120 else "")
        citations = item.get("sourceCitations") or []
        doc_ref = citations[0].get("docId", "") if citations else ""
        snippet_ref = citations[0].get("snippet", "").replace("\n", " ") if citations else ""
        if len(snippet_ref) > 140:
            snippet_ref = snippet_ref[:140] + "..."

        writer.writerow([
            f"Q{idx}",
            item.get("id", f"item-{idx}"),
            f"Version {version_label}",
            q_type,
            item.get("marks", 1),
            item.get("cloId", "CLO1"),
            item.get("topicId", "Core"),
            item.get("bloom", "understand").capitalize(),
            item.get("difficulty", 3),
            item.get("key", "A"),
            stem_excerpt,
            doc_ref,
            snippet_ref,
        ])

    return output.getvalue()
