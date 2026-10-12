"""
PDF Report Builder — renders the dark-themed HireFlow candidate analysis
report using ReportLab.
"""
from __future__ import annotations

import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import Color, HexColor
from reportlab.pdfgen.canvas import Canvas

from app.services.pdf_analysis_service import PDFReportData

# ─── Page Setup ───────────────────────────────────────────────────────────────

PAGE_W, PAGE_H = A4  # 595.27 × 841.89 pt
MARGIN = 30
CONTENT_W = PAGE_W - 2 * MARGIN
CARD_PAD = 10
LINE_H = 14  # default line height

# ─── Colour Palette ──────────────────────────────────────────────────────────

BG = HexColor("#0F0F14")
CARD_BG = HexColor("#1A1A24")
CARD_BG_LIGHTER = HexColor("#22222E")
TEXT_WHITE = Color(1, 1, 1)
TEXT_GREY = HexColor("#B0B0B8")
TEXT_LIGHT = HexColor("#808088")
DIVIDER = HexColor("#2A2A36")

# Accent colours
PURPLE = HexColor("#8B47DE")
PINK = HexColor("#E04590")
GREEN = HexColor("#33C75A")
RED = HexColor("#E04040")
BLUE = HexColor("#4080F0")
ORANGE = HexColor("#F08C28")
YELLOW = HexColor("#F0CC30")
CYAN = HexColor("#30C8D0")
TEAL = HexColor("#20B090")

# Progress bar track
TRACK_BG = HexColor("#2A2A36")

# Badge colours by stack category
BADGE_COLORS = {
    "Languages": HexColor("#4080F0"),
    "Cloud": HexColor("#F08C28"),
    "Frameworks": HexColor("#8B47DE"),
    "Databases": HexColor("#33C75A"),
    "DevOps": HexColor("#E04590"),
    "Other": HexColor("#30C8D0"),
    "Tools & Technologies": HexColor("#4080F0"),
}

SKILL_CAT_COLORS = {
    "Strategic": BLUE,
    "Technical": PURPLE,
    "Functional": ORANGE,
    "Leadership": GREEN,
}


class PDFReportBuilder:
    """Renders PDFReportData into a dark-themed PDF byte stream."""

    def build(self, data: PDFReportData) -> bytes:
        buf = io.BytesIO()
        self.c = Canvas(buf, pagesize=A4)
        self.y = PAGE_H  # current y position (decrements downward)
        self.data = data

        # Fill first page background
        self._fill_page_bg()

        # Render sections top-to-bottom
        self._draw_header()
        self._draw_hero_banner()
        self._draw_executive_summary()
        self._draw_career_trajectory()
        self._draw_tenure_section()
        self._draw_role_type()
        self._draw_market_exposure()
        self._draw_company_type()
        self._draw_industry_exposure()
        self._draw_achievements()
        self._draw_skills_categories()
        self._draw_technical_stack()
        self._draw_strengths()
        self._draw_weaknesses()
        self._draw_why_shortlist()
        self._draw_score_cards()
        self._draw_footer()

        self.c.save()
        buf.seek(0)
        return buf.read()

    # ─── Page Management ──────────────────────────────────────────────────

    def _fill_page_bg(self):
        self.c.setFillColor(BG)
        self.c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    def _ensure_space(self, needed: float):
        """If not enough vertical space, start a new page."""
        if self.y - needed < MARGIN + 30:  # 30pt buffer for footer
            self._draw_footer()
            self.c.showPage()
            self._fill_page_bg()
            self.y = PAGE_H - MARGIN

    # ─── Drawing Helpers ──────────────────────────────────────────────────

    def _draw_rounded_rect(self, x, y, w, h, r=6, fill_color=CARD_BG):
        """Draw a rounded rectangle card."""
        self.c.setFillColor(fill_color)
        self.c.setStrokeColor(fill_color)
        self.c.roundRect(x, y, w, h, r, fill=1, stroke=0)

    def _draw_progress_bar(self, x, y, w, h, pct, bar_color=BLUE):
        """Draw a progress bar with dark track and coloured fill."""
        # Track
        self.c.setFillColor(TRACK_BG)
        self.c.roundRect(x, y, w, h, h / 2, fill=1, stroke=0)
        # Fill
        fill_w = max(h, w * min(pct, 100) / 100)
        self.c.setFillColor(bar_color)
        self.c.roundRect(x, y, fill_w, h, h / 2, fill=1, stroke=0)

    def _draw_circle_score(self, cx, cy, r, score, color=BLUE):
        """Draw a circular score indicator (arc + number)."""
        # Background circle
        self.c.setStrokeColor(TRACK_BG)
        self.c.setLineWidth(3)
        self.c.circle(cx, cy, r, fill=0, stroke=1)
        # Foreground arc
        self.c.setStrokeColor(color)
        self.c.setLineWidth(3)
        angle = 360 * min(score, 100) / 100
        # ReportLab arc: x1,y1,x2,y2,startAng,extent
        self.c.arc(cx - r, cy - r, cx + r, cy + r, 90, -angle)
        # Score number
        self.c.setFillColor(TEXT_WHITE)
        self.c.setFont("Helvetica-Bold", 11)
        self.c.drawCentredString(cx, cy - 4, str(int(score)))

    def _draw_badge(self, x, y, text, bg_color=BLUE):
        """Draw a small coloured badge/tag. Returns the badge width."""
        self.c.setFont("Helvetica", 7)
        tw = self.c.stringWidth(text, "Helvetica", 7)
        pad = 6
        bw = tw + pad * 2
        bh = 14
        self.c.setFillColor(bg_color)
        self.c.roundRect(x, y, bw, bh, 3, fill=1, stroke=0)
        self.c.setFillColor(TEXT_WHITE)
        self.c.drawString(x + pad, y + 4, text)
        return bw

    def _section_title(self, title: str, y_offset: float = 0):
        """Draw a section title with a thin divider line."""
        self.y -= (14 + y_offset)
        self.c.setFillColor(TEXT_WHITE)
        self.c.setFont("Helvetica-Bold", 11)
        self.c.drawString(MARGIN + CARD_PAD, self.y, title)
        self.y -= 6
        self.c.setStrokeColor(DIVIDER)
        self.c.setLineWidth(0.5)
        self.c.line(MARGIN + CARD_PAD, self.y, PAGE_W - MARGIN - CARD_PAD, self.y)
        self.y -= 14

    def _wrap_text(self, text: str, font: str, size: float, max_w: float) -> list[str]:
        """Simple word-wrap returning list of lines."""
        words = text.split()
        lines = []
        current = ""
        for w in words:
            test = f"{current} {w}".strip()
            if self.c.stringWidth(test, font, size) <= max_w:
                current = test
            else:
                if current:
                    lines.append(current)
                current = w
        if current:
            lines.append(current)
        return lines or [""]

    # ─── Section 1: Header Bar ────────────────────────────────────────────

    def _draw_header(self):
        h = 28
        self.y = PAGE_H - MARGIN
        self._draw_rounded_rect(MARGIN, self.y - h, CONTENT_W, h, fill_color=CARD_BG)
        self.c.setFillColor(TEXT_GREY)
        self.c.setFont("Helvetica-Bold", 9)
        self.c.drawString(MARGIN + CARD_PAD, self.y - 18, "HireFlow — Candidate Overview")
        # "Review & Provide Feedback" pill on right
        pill_text = "Review & Provide Feedback"
        tw = self.c.stringWidth(pill_text, "Helvetica", 7)
        px = PAGE_W - MARGIN - CARD_PAD - tw - 12
        self.c.setFillColor(PURPLE)
        self.c.roundRect(px, self.y - 21, tw + 12, 16, 3, fill=1, stroke=0)
        self.c.setFillColor(TEXT_WHITE)
        self.c.setFont("Helvetica", 7)
        self.c.drawString(px + 6, self.y - 17, pill_text)
        self.y -= (h + 6)

    # ─── Section 2: Hero Banner ───────────────────────────────────────────

    def _draw_hero_banner(self):
        h = 90
        self._ensure_space(h + 10)
        bx, by = MARGIN, self.y - h

        # Gradient background (purple left → pink right) via linearGradient
        self.c.saveState()
        p = self.c.beginPath()
        r = 6
        # Rounded rect path
        p.moveTo(bx + r, by)
        p.lineTo(bx + CONTENT_W - r, by)
        p.arcTo(bx + CONTENT_W - 2 * r, by, bx + CONTENT_W, by + 2 * r, -90, 90)
        p.lineTo(bx + CONTENT_W, by + h - r)
        p.arcTo(bx + CONTENT_W - 2 * r, by + h - 2 * r, bx + CONTENT_W, by + h, 0, 90)
        p.lineTo(bx + r, by + h)
        p.arcTo(bx, by + h - 2 * r, bx + 2 * r, by + h, 90, 90)
        p.lineTo(bx, by + r)
        p.arcTo(bx, by, bx + 2 * r, by + 2 * r, 180, 90)
        p.close()
        self.c.clipPath(p, stroke=0)
        self.c.linearGradient(bx, by + h / 2, bx + CONTENT_W, by + h / 2,
                              (PURPLE, PINK))
        self.c.restoreState()

        # Candidate name
        self.c.setFillColor(TEXT_WHITE)
        self.c.setFont("Helvetica-Bold", 20)
        name = self.data.candidate_name
        self.c.drawString(bx + 15, by + h - 30, name)

        # Current title
        self.c.setFont("Helvetica", 10)
        self.c.drawString(bx + 15, by + h - 46, self.data.current_title)

        # Info pills
        pills = [
            self.data.location,
            f"{self.data.years_of_experience} yrs exp",
            self.data.education_level,
        ]
        px = bx + 15
        pill_y = by + 12
        self.c.setFont("Helvetica", 7)
        for pill in pills:
            if not pill or pill == "Not specified":
                continue
            tw = self.c.stringWidth(pill, "Helvetica", 7)
            pw = tw + 12
            # Pill background (semi-transparent white)
            self.c.setFillColor(Color(1, 1, 1, 0.2))
            self.c.roundRect(px, pill_y, pw, 16, 3, fill=1, stroke=0)
            self.c.setFillColor(TEXT_WHITE)
            self.c.drawString(px + 6, pill_y + 4, pill)
            px += pw + 6

        # Match Score box (top-right)
        score_box_w = 70
        score_box_h = 55
        sx = bx + CONTENT_W - score_box_w - 12
        sy = by + h - score_box_h - 10
        self.c.setFillColor(Color(0, 0, 0, 0.3))
        self.c.roundRect(sx, sy, score_box_w, score_box_h, 6, fill=1, stroke=0)
        self.c.setFillColor(TEXT_WHITE)
        self.c.setFont("Helvetica-Bold", 28)
        self.c.drawCentredString(sx + score_box_w / 2, sy + 22, str(int(self.data.match_score)))
        self.c.setFont("Helvetica", 7)
        self.c.drawCentredString(sx + score_box_w / 2, sy + 8, "Match Score")

        self.y -= (h + 8)

    # ─── Section 3: Executive Summary ─────────────────────────────────────

    def _draw_executive_summary(self):
        text = self.data.executive_summary or "Executive summary not available."
        lines = self._wrap_text(text, "Helvetica", 9, CONTENT_W - 2 * CARD_PAD)
        card_h = 18 + len(lines) * LINE_H + 10
        self._ensure_space(card_h + 10)
        self._section_title("Executive Summary")
        self.c.setFillColor(TEXT_GREY)
        self.c.setFont("Helvetica", 9)
        for line in lines:
            self.c.drawString(MARGIN + CARD_PAD, self.y, line)
            self.y -= LINE_H
        self.y -= 8

    # ─── Section 4: Career Trajectory Snapshot ────────────────────────────

    def _draw_career_trajectory(self):
        timeline = self.data.career_timeline
        card_h = 110
        self._ensure_space(card_h)
        self._section_title("Career Trajectory Snapshot")

        if not timeline:
            self.c.setFillColor(TEXT_GREY)
            self.c.setFont("Helvetica", 9)
            self.c.drawString(MARGIN + CARD_PAD, self.y, "No experience data available.")
            self.y -= 20
            return

        # Draw timeline: circles connected by a line (most recent on right)
        reversed_tl = list(reversed(timeline))  # oldest left → newest right
        n = len(reversed_tl)
        spacing = min(180, (CONTENT_W - 60) / max(n, 1))
        start_x = MARGIN + 40
        line_y = self.y - 5

        # Connecting line
        if n > 1:
            self.c.setStrokeColor(TEXT_LIGHT)
            self.c.setLineWidth(1.5)
            self.c.line(start_x, line_y, start_x + (n - 1) * spacing, line_y)

        for i, role in enumerate(reversed_tl):
            cx = start_x + i * spacing
            # Circle
            self.c.setFillColor(PURPLE)
            self.c.circle(cx, line_y, 8, fill=1, stroke=0)
            # Year inside circle
            yr = role.get("year", "")
            if len(yr) >= 4:
                yr = "'" + yr[2:4]
            self.c.setFillColor(TEXT_WHITE)
            self.c.setFont("Helvetica-Bold", 6)
            self.c.drawCentredString(cx, line_y - 2, yr)
            # Title below
            self.c.setFillColor(TEXT_WHITE)
            self.c.setFont("Helvetica-Bold", 7)
            title = role.get("title", "")[:25]
            self.c.drawCentredString(cx, line_y - 22, title)
            # Company below title
            self.c.setFillColor(TEXT_GREY)
            self.c.setFont("Helvetica", 6)
            company = role.get("company", "")[:25]
            self.c.drawCentredString(cx, line_y - 32, company)

        self.y = line_y - 48

        # Facts below timeline
        facts = [
            f"Promotion frequency: {self.data.promotion_frequency}",
            f"Career breaks: {self.data.career_breaks}",
            f"Locations: {self.data.cities_worked}",
        ]
        self.c.setFont("Helvetica", 8)
        self.c.setFillColor(TEXT_GREY)
        for fact in facts:
            self.c.drawString(MARGIN + CARD_PAD, self.y, fact)
            self.y -= 13
        self.y -= 8

    # ─── Section 5: Average Tenure ────────────────────────────────────────

    def _draw_tenure_section(self):
        self._ensure_space(80)
        self._section_title("Average Tenure")

        self.y -= 6  # extra breathing room after title

        col_w = CONTENT_W / 3
        labels = ["Overall Average", "Last 3 Roles", "Longest Tenure"]
        values = [self.data.avg_tenure_overall, self.data.avg_tenure_last3, self.data.longest_tenure]

        for i, (lbl, val) in enumerate(zip(labels, values)):
            cx = MARGIN + col_w * i + col_w / 2
            # Value
            self.c.setFillColor(TEXT_WHITE)
            self.c.setFont("Helvetica-Bold", 20)
            self.c.drawCentredString(cx, self.y, f"{val}")
            # "years" label
            self.c.setFillColor(TEXT_GREY)
            self.c.setFont("Helvetica", 7)
            self.c.drawCentredString(cx, self.y - 16, "years")
            # Description
            self.c.setFont("Helvetica", 8)
            self.c.drawCentredString(cx, self.y - 30, lbl)

        self.y -= 48

    # ─── Section 6: Time by Role Type ─────────────────────────────────────

    def _draw_role_type(self):
        self._ensure_space(70)
        self._section_title("Time by Role Type")
        self._draw_bar_section(self.data.role_type_breakdown, PURPLE)

    # ─── Section 7: Global Market Exposure ────────────────────────────────

    def _draw_market_exposure(self):
        self._ensure_space(70)
        self._section_title("Global Market Exposure")
        self._draw_bar_section(self.data.global_market_exposure, BLUE)

    # ─── Section 8: Time by Company Type ──────────────────────────────────

    def _draw_company_type(self):
        self._ensure_space(55)
        self._section_title("Time by Company Type")
        self._draw_bar_section(self.data.company_type_breakdown, TEAL)

    def _draw_bar_section(self, data_dict: dict, bar_color: Color):
        """Generic helper to draw labelled horizontal progress bars."""
        bar_w = CONTENT_W - 2 * CARD_PAD - 140
        for label, pct in data_dict.items():
            pct_val = float(pct) if pct else 0
            self.c.setFillColor(TEXT_GREY)
            self.c.setFont("Helvetica", 8)
            self.c.drawString(MARGIN + CARD_PAD, self.y, label)
            # Progress bar
            bar_x = MARGIN + CARD_PAD + 130
            self._draw_progress_bar(bar_x, self.y - 2, bar_w, 8, pct_val, bar_color)
            # Percentage text
            self.c.setFillColor(TEXT_WHITE)
            self.c.setFont("Helvetica-Bold", 8)
            self.c.drawRightString(PAGE_W - MARGIN - CARD_PAD, self.y, f"{int(pct_val)}%")
            self.y -= 18
        self.y -= 6

    # ─── Section 9: Industry Exposure ─────────────────────────────────────

    def _draw_industry_exposure(self):
        industries = self.data.industry_exposure[:3]
        if not industries:
            return
        self._ensure_space(60)
        self._section_title("Industry Exposure")

        col_w = CONTENT_W / max(len(industries), 1)
        for i, ind in enumerate(industries):
            cx = MARGIN + col_w * i + col_w / 2
            pct = ind.get("percentage", 0)
            name = ind.get("industry", "Unknown")
            self.c.setFillColor(TEXT_WHITE)
            self.c.setFont("Helvetica-Bold", 20)
            self.c.drawCentredString(cx, self.y, f"{int(pct)}%")
            self.c.setFillColor(TEXT_GREY)
            self.c.setFont("Helvetica", 8)
            self.c.drawCentredString(cx, self.y - 16, name)

        self.y -= 30

    # ─── Section 10: Key Achievements ─────────────────────────────────────

    def _draw_achievements(self):
        items = self.data.key_achievements[:5]
        if not items:
            return
        card_h = 18 + len(items) * LINE_H + 10
        self._ensure_space(card_h)
        self._section_title("Key Achievements")

        self.c.setFont("Helvetica", 8)
        max_w = CONTENT_W - 2 * CARD_PAD - 12
        for item in items:
            # Accent dot
            self.c.setFillColor(CYAN)
            self.c.circle(MARGIN + CARD_PAD + 3, self.y + 3, 2.5, fill=1, stroke=0)
            # Text (may wrap)
            lines = self._wrap_text(item, "Helvetica", 8, max_w)
            self.c.setFillColor(TEXT_GREY)
            for line in lines:
                self.c.drawString(MARGIN + CARD_PAD + 12, self.y, line)
                self.y -= LINE_H
        self.y -= 8

    # ─── Section 11: Skills (4 Categories) ────────────────────────────────

    def _draw_skills_categories(self):
        cats = self.data.skills_categorized
        if not any(cats.values()):
            return
        self._ensure_space(80)
        self._section_title("Skills")

        col_w = CONTENT_W / 2
        items = list(cats.items())
        row_y = self.y

        for idx, (cat, skills) in enumerate(items):
            col = idx % 2
            if idx == 2:
                row_y = self.y
            x = MARGIN + CARD_PAD + col * col_w
            color = SKILL_CAT_COLORS.get(cat, BLUE)
            # Category label
            self.c.setFillColor(color)
            self.c.setFont("Helvetica-Bold", 8)
            self.c.drawString(x, row_y, cat)
            # Skills list
            self.c.setFillColor(TEXT_GREY)
            self.c.setFont("Helvetica", 7)
            skill_text = ", ".join(skills[:8])
            lines = self._wrap_text(skill_text, "Helvetica", 7, col_w - 20)
            ty = row_y - 12
            for line in lines:
                self.c.drawString(x, ty, line)
                ty -= 10

            if col == 1:
                self.y = min(self.y, ty - 6)

        if len(items) % 2 == 1:
            self.y = min(self.y, row_y - 30)
        self.y -= 10

    # ─── Section 12: Technical Stack ──────────────────────────────────────

    def _draw_technical_stack(self):
        stack = self.data.technical_stack
        if not stack:
            return
        self._ensure_space(60)
        self._section_title("Technical Stack")

        self.y -= 4  # breathing room before badges

        bx = MARGIN + CARD_PAD
        by = self.y
        max_x = PAGE_W - MARGIN - CARD_PAD

        for category, items in stack.items():
            if not items:
                continue
            color = BADGE_COLORS.get(category, BLUE)
            for item in items[:10]:
                badge_w = self._draw_badge(bx, by, item, color)
                bx += badge_w + 4
                if bx + 40 > max_x:
                    bx = MARGIN + CARD_PAD
                    by -= 18
                    self._ensure_space(20)

            bx += 8  # gap between categories

        self.y = by - 18

    # ─── Section 13: Strengths ────────────────────────────────────────────

    def _draw_strengths(self):
        items = self.data.strengths[:5]
        if not items:
            return
        card_h = 26 + len(items) * LINE_H + 10
        self._ensure_space(card_h)

        # Green stripe card
        card_y = self.y - card_h + 10
        self._draw_rounded_rect(MARGIN, card_y, CONTENT_W, card_h, fill_color=CARD_BG)
        # Green top stripe
        self.c.setFillColor(GREEN)
        self.c.rect(MARGIN, card_y + card_h - 3, CONTENT_W, 3, fill=1, stroke=0)

        self.y -= 8
        self.c.setFillColor(TEXT_WHITE)
        self.c.setFont("Helvetica-Bold", 10)
        self.c.drawString(MARGIN + CARD_PAD, self.y, "Strengths")
        self.y -= 14

        self.c.setFont("Helvetica", 8)
        for item in items:
            lines = self._wrap_text(item, "Helvetica", 8, CONTENT_W - 2 * CARD_PAD - 12)
            # Green dot
            self.c.setFillColor(GREEN)
            self.c.circle(MARGIN + CARD_PAD + 3, self.y + 3, 2.5, fill=1, stroke=0)
            self.c.setFillColor(TEXT_GREY)
            for line in lines:
                self.c.drawString(MARGIN + CARD_PAD + 12, self.y, line)
                self.y -= LINE_H
        self.y -= 10

    # ─── Section 14: Weaknesses / Gaps ────────────────────────────────────

    def _draw_weaknesses(self):
        items = self.data.weaknesses[:4]
        if not items:
            return
        card_h = 26 + len(items) * LINE_H + 10
        self._ensure_space(card_h)

        card_y = self.y - card_h + 10
        self._draw_rounded_rect(MARGIN, card_y, CONTENT_W, card_h, fill_color=CARD_BG)
        # Red top stripe
        self.c.setFillColor(RED)
        self.c.rect(MARGIN, card_y + card_h - 3, CONTENT_W, 3, fill=1, stroke=0)

        self.y -= 8
        self.c.setFillColor(TEXT_WHITE)
        self.c.setFont("Helvetica-Bold", 10)
        self.c.drawString(MARGIN + CARD_PAD, self.y, "Weaknesses / Gaps")
        self.y -= 14

        self.c.setFont("Helvetica", 8)
        for item in items:
            lines = self._wrap_text(item, "Helvetica", 8, CONTENT_W - 2 * CARD_PAD - 12)
            self.c.setFillColor(RED)
            self.c.circle(MARGIN + CARD_PAD + 3, self.y + 3, 2.5, fill=1, stroke=0)
            self.c.setFillColor(TEXT_GREY)
            for line in lines:
                self.c.drawString(MARGIN + CARD_PAD + 12, self.y, line)
                self.y -= LINE_H
        self.y -= 10

    # ─── Section 15: Why Shortlist ────────────────────────────────────────

    def _draw_why_shortlist(self):
        text = self.data.why_shortlist
        if not text:
            return
        lines = self._wrap_text(text, "Helvetica", 9, CONTENT_W - 2 * CARD_PAD)
        card_h = 30 + len(lines) * LINE_H + 20
        self._ensure_space(card_h)
        self._section_title("Why Shortlist This Candidate?")

        self.c.setFillColor(TEXT_GREY)
        self.c.setFont("Helvetica", 9)
        for line in lines:
            self.c.drawString(MARGIN + CARD_PAD, self.y, line)
            self.y -= LINE_H

        # Verdict badge
        self.y -= 14
        verdict = self.data.verdict
        verdict_color = {
            "STRONGLY RECOMMEND": GREEN,
            "RECOMMEND": BLUE,
            "CONSIDER": ORANGE,
            "PASS": RED,
        }.get(verdict, TEXT_GREY)

        self.c.setFillColor(verdict_color)
        self.c.setFont("Helvetica-Bold", 10)
        tw = self.c.stringWidth(verdict, "Helvetica-Bold", 10)
        vx = MARGIN + CARD_PAD
        self.c.roundRect(vx, self.y - 4, tw + 16, 20, 4, fill=1, stroke=0)
        self.c.setFillColor(TEXT_WHITE)
        self.c.drawString(vx + 8, self.y, verdict)
        self.y -= 28

    # ─── Section 16: Analysis Score Cards ─────────────────────────────────

    def _draw_score_cards(self):
        scores = self.data.analysis_scores
        if not scores:
            return
        card_h = 160
        self._ensure_space(card_h)
        self._section_title("Analysis Score Cards")

        cards_data = [
            ("Alignment", scores.get("alignment", {}), BLUE, "Higher is better"),
            ("Divergence", scores.get("divergence", {}), ORANGE, "Lower is better"),
            ("Compatibility", scores.get("compatibility", {}), GREEN, "Higher is better"),
            ("Concerns", scores.get("concerns", {}), RED, "Lower is better"),
        ]

        col_w = (CONTENT_W - 12) / 4
        card_inner_h = 130
        base_y = self.y - card_inner_h

        for i, (title, card_data, color, hint) in enumerate(cards_data):
            x = MARGIN + i * (col_w + 4)
            # Card background
            self._draw_rounded_rect(x, base_y, col_w, card_inner_h, fill_color=CARD_BG)

            # Title
            self.c.setFillColor(TEXT_WHITE)
            self.c.setFont("Helvetica-Bold", 8)
            self.c.drawCentredString(x + col_w / 2, base_y + card_inner_h - 14, title)

            # Hint
            self.c.setFillColor(TEXT_LIGHT)
            self.c.setFont("Helvetica", 6)
            self.c.drawCentredString(x + col_w / 2, base_y + card_inner_h - 24, hint)

            # Circular score
            score = card_data.get("score", 0)
            self._draw_circle_score(x + col_w / 2, base_y + card_inner_h - 52, 18, score, color)

            # Fitness label
            fitness = card_data.get("fitness", "Medium")
            self.c.setFillColor(color)
            self.c.setFont("Helvetica-Bold", 7)
            self.c.drawCentredString(x + col_w / 2, base_y + card_inner_h - 78, f"Fitness: {fitness}")

            # Bullet points
            bullets = card_data.get("bullets", [])[:3]
            self.c.setFont("Helvetica", 6)
            self.c.setFillColor(TEXT_GREY)
            by = base_y + card_inner_h - 92
            for bullet in bullets:
                # Truncate long bullets
                text = bullet[:50] + "..." if len(bullet) > 50 else bullet
                lines = self._wrap_text(text, "Helvetica", 6, col_w - 12)
                for line in lines:
                    if by < base_y + 4:
                        break
                    self.c.drawString(x + 6, by, f"• {line}")
                    by -= 9

        self.y = base_y - 8

    # ─── Section 17: Footer ───────────────────────────────────────────────

    def _draw_footer(self):
        footer_text = "Generated via HireFlow AI (experimental). Copyright 2024. All rights reserved."
        self.c.setFillColor(TEXT_LIGHT)
        self.c.setFont("Helvetica", 6)
        self.c.drawCentredString(PAGE_W / 2, MARGIN - 10, footer_text)
