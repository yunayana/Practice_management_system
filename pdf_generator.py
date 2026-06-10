"""
Etap 11 – Generowanie dokumentów PDF.

Funkcje:
  generate_confirmation_pdf(data)  → BytesIO z PDF potwierdzenia efektów uczenia się
  generate_journal_pdf(data)       → BytesIO z PDF dziennika praktyki
  generate_report_pdf(conf, jour)  → BytesIO z PDF raportu końcowego (oba dokumenty)

Użycie w Flask:
  from pdf_generator import generate_confirmation_pdf
  buf = generate_confirmation_pdf(student_data)
  return send_file(buf, mimetype="application/pdf",
                   download_name="potwierdzenie.pdf", as_attachment=True)

Wymagania:
  pip install reportlab
"""
from __future__ import annotations

import io
import os
from datetime import date

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, PageBreak, HRFlowable
)

# ─────────────────────────────────────────────────────────────────────────────
# Rejestracja fontu z obsługą polskich znaków
# ─────────────────────────────────────────────────────────────────────────────

_FONT_NAME  = "MainFont"
_FONT_BOLD  = "MainFontBold"
_REGISTERED = False

def _register_fonts() -> None:
    global _REGISTERED, _FONT_NAME, _FONT_BOLD
    if _REGISTERED:
        return

    # Kandydaci na fonty (Windows → Linux)
    regular_candidates = [
        r"C:\Windows\Fonts\calibri.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\tahoma.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    bold_candidates = [
        r"C:\Windows\Fonts\calibrib.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\tahomabd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]

    def _try_register(name: str, candidates: list[str]) -> bool:
        for path in candidates:
            if os.path.exists(path):
                pdfmetrics.registerFont(TTFont(name, path))
                return True
        return False

    if not _try_register(_FONT_NAME, regular_candidates):
        # Fallback do wbudowanego Helvetica (bez polskich znaków)
        _FONT_NAME = "Helvetica"
        _FONT_BOLD = "Helvetica-Bold"
        _REGISTERED = True
        return

    if not _try_register(_FONT_BOLD, bold_candidates):
        _FONT_BOLD = _FONT_NAME

    _REGISTERED = True


# ─────────────────────────────────────────────────────────────────────────────
# Style dokumentu
# ─────────────────────────────────────────────────────────────────────────────

def _get_styles() -> dict:
    _register_fonts()
    base = getSampleStyleSheet()
    fn, fb = _FONT_NAME, _FONT_BOLD

    return {
        "title": ParagraphStyle(
            "title", fontName=fb, fontSize=14, alignment=TA_CENTER,
            spaceAfter=4, textColor=colors.HexColor("#1F3864"),
        ),
        "subtitle": ParagraphStyle(
            "subtitle", fontName=fn, fontSize=10, alignment=TA_CENTER,
            spaceAfter=12, textColor=colors.HexColor("#444444"),
        ),
        "section": ParagraphStyle(
            "section", fontName=fb, fontSize=11, spaceBefore=12, spaceAfter=4,
            textColor=colors.HexColor("#2E5FA3"),
        ),
        "normal": ParagraphStyle(
            "normal", fontName=fn, fontSize=9, leading=13, alignment=TA_LEFT,
        ),
        "normal_center": ParagraphStyle(
            "normal_center", fontName=fn, fontSize=9, leading=13, alignment=TA_CENTER,
        ),
        "justify": ParagraphStyle(
            "justify", fontName=fn, fontSize=9, leading=13, alignment=TA_JUSTIFY,
        ),
        "label": ParagraphStyle(
            "label", fontName=fb, fontSize=9,
        ),
        "small": ParagraphStyle(
            "small", fontName=fn, fontSize=8, textColor=colors.HexColor("#666666"),
        ),
        "footer": ParagraphStyle(
            "footer", fontName=fn, fontSize=7, alignment=TA_CENTER,
            textColor=colors.HexColor("#999999"),
        ),
    }


def _table_style_default() -> TableStyle:
    return TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor("#2E5FA3")),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",      (0, 0), (-1, 0),  _FONT_BOLD),
        ("FONTSIZE",      (0, 0), (-1, 0),  9),
        ("ALIGN",         (0, 0), (-1, 0),  "CENTER"),
        ("FONTNAME",      (0, 1), (-1, -1), _FONT_NAME),
        ("FONTSIZE",      (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#EEF4FF")]),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])


def _header_block(elements: list, title: str, subtitle: str, styles: dict) -> None:
    elements.append(Paragraph("Akademia Nauk Stosowanych w Elblągu", styles["subtitle"]))
    elements.append(Paragraph(title, styles["title"]))
    if subtitle:
        elements.append(Paragraph(subtitle, styles["subtitle"]))
    elements.append(HRFlowable(width="100%", thickness=1.5,
                                color=colors.HexColor("#2E5FA3"), spaceAfter=8))


def _footer_text(styles: dict) -> list:
    today = date.today().strftime("%d.%m.%Y")
    return [
        Spacer(1, 0.5 * cm),
        HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CCCCCC")),
        Paragraph(f"Wygenerowano: {today} | System obsługi praktyk – ANS Elbląg",
                  styles["footer"]),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# 1. Potwierdzenie efektów uczenia się (Załącznik nr 4)
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# Pomocnicze funkcje – odporność na błędne dane (Zadanie 6)
# ─────────────────────────────────────────────────────────────────────────────

def _safe_str(value, default: str = "–", max_len: int = 2000) -> str:
    """Konwertuje dowolną wartość na bezpieczny ciąg znaków."""
    if value is None:
        return default
    s = str(value).strip()
    if not s:
        return default
    # Obcięcie bardzo długich tekstów (zabezpieczenie przed przepełnieniem tabeli)
    if len(s) > max_len:
        s = s[:max_len] + "… [tekst skrócony]"
    return s


def _safe_para(value, style, default: str = "–", max_len: int = 2000) -> Paragraph:
    """Zwraca Paragraph z bezpiecznym tekstem."""
    return Paragraph(_safe_str(value, default, max_len), style)


EFFECTS_LIST = [
    ("01", "Ma wiedzę na temat sposobu realizacji zadań inżynierskich dotyczących informatyki z zachowaniem standardów i norm technicznych"),
    ("02", "Zna technologie, narzędzia, metody, techniki oraz sprzęt stosowane w informatyce"),
    ("03", "Zna ekonomiczne i prawne skutki własnych działań oraz ograniczenia prawa autorskiego i kodeksu pracy"),
    ("04", "Zna zasady bezpieczeństwa pracy i ergonomii w zawodzie informatyka"),
    ("05", "Pozyskuje informacje o technologiach, metodach i sprzęcie z różnych źródeł"),
    ("06", "Rozwija kompetencje w zakresie sprzętu i oprogramowania"),
    ("07", "Opracowuje dokumentację i referuje zagadnienia"),
    ("08", "Identyfikuje problem informatyczny i realizuje rozwiązanie"),
    ("09", "Rozwiązuje rzeczywiste zadanie inżynierskie z uwzględnieniem norm i etyki"),
    ("10", "Pracuje w zespole branży IT"),
    ("11", "Przestrzega zasad etyki zawodowej"),
    ("12", "Komunikuje zagadnienia informatyczne osobom spoza branży"),
    ("13", "Dostrzega tempo deaktualizacji wiedzy informatycznej"),
]


def generate_confirmation_pdf(data: dict) -> io.BytesIO:
    """
    Generuje PDF potwierdzenia efektów uczenia się (Załącznik nr 4).

    Parametry data (słownik z formularza):
      student_name, album, specialty, hours,
      effects (dict: '01'→True/False, …),
      company_supervisor_note, university_supervisor_opinion

    Odporność: brakujące pola zastępowane „–"; długie teksty skracane automatycznie.
    """
    if not data:
        data = {}
    _register_fonts()
    styles = _get_styles()
    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )
    elements = []

    # ── Nagłówek ──────────────────────────────────────────────────────────────
    _header_block(elements,
                  "Potwierdzenie efektów uczenia się",
                  "Załącznik nr 4 – praktyka zawodowa studentów informatyki",
                  styles)

    # ── Dane studenta ─────────────────────────────────────────────────────────
    elements.append(Paragraph("Dane studenta", styles["section"]))
    student_data = [
        ["Student/ka:", _safe_str(data.get("student_name")),
         "Nr albumu:", _safe_str(data.get("album"))],
        ["Specjalność:", _safe_str(data.get("specialty")),
         "Liczba godzin:", _safe_str(data.get("hours"))],
    ]
    st = Table(student_data, colWidths=[3.5*cm, 7*cm, 3*cm, 3*cm])
    st.setStyle(TableStyle([
        ("FONTNAME",      (0, 0), (0, -1), _FONT_BOLD),
        ("FONTNAME",      (2, 0), (2, -1), _FONT_BOLD),
        ("FONTNAME",      (1, 0), (1, -1), _FONT_NAME),
        ("FONTNAME",      (3, 0), (3, -1), _FONT_NAME),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("LINEBELOW",     (0, 0), (-1, -1), 0.3, colors.HexColor("#CCCCCC")),
    ]))
    elements.append(st)
    elements.append(Spacer(1, 0.4*cm))

    # ── Tabela efektów ────────────────────────────────────────────────────────
    elements.append(Paragraph("Efekty uczenia się", styles["section"]))

    effects = data.get("effects") or {}
    if not isinstance(effects, dict):
        effects = {}
    table_data = [["Nr", "Opis efektu uczenia się", "Uzyskano"]]
    for nr, opis in EFFECTS_LIST:
        achieved = bool(effects.get(nr, False))
        mark = "✓" if achieved else "–"
        table_data.append([nr, Paragraph(opis, styles["normal"]), mark])

    eff_table = Table(table_data, colWidths=[1*cm, 13.5*cm, 2*cm])
    ts = _table_style_default()
    ts.add("ALIGN", (0, 0), (0, -1), "CENTER")
    ts.add("ALIGN", (2, 0), (2, -1), "CENTER")
    # Kolorowanie osiągniętych efektów
    for i, (nr, _) in enumerate(EFFECTS_LIST, start=1):
        if effects.get(nr, False):
            ts.add("TEXTCOLOR", (2, i), (2, i), colors.HexColor("#16a34a"))
            ts.add("FONTNAME",  (2, i), (2, i), _FONT_BOLD)
    eff_table.setStyle(ts)
    elements.append(eff_table)
    elements.append(Spacer(1, 0.5*cm))

    # ── Potwierdzenie opiekuna zakładowego ────────────────────────────────────
    elements.append(Paragraph("Potwierdzenie opiekuna zakładowego", styles["section"]))
    note = _safe_str(data.get("company_supervisor_note"), default="Brak uwag.", max_len=1000)
    elements.append(Paragraph(note, styles["justify"]))
    elements.append(Spacer(1, 0.4*cm))

    # Linia podpisu
    sig_data = [["", ""],
                ["Data i podpis opiekuna zakładowego:", ""]]
    sig = Table(sig_data, colWidths=[10*cm, 6.5*cm])
    sig.setStyle(TableStyle([
        ("LINEABOVE",  (1, 1), (1, 1), 0.5, colors.black),
        ("ALIGN",      (0, 1), (0, 1), "LEFT"),
        ("FONTNAME",   (0, 0), (-1, -1), _FONT_NAME),
        ("FONTSIZE",   (0, 0), (-1, -1), 8),
    ]))
    elements.append(sig)
    elements.append(Spacer(1, 0.4*cm))

    # ── Opinia opiekuna uczelnianego ──────────────────────────────────────────
    elements.append(Paragraph("Opinia opiekuna uczelnianego", styles["section"]))
    opinion = _safe_str(data.get("university_supervisor_opinion"), default="Brak opinii.", max_len=1000)
    elements.append(Paragraph(opinion, styles["justify"]))
    elements.append(Spacer(1, 0.4*cm))

    sig2_data = [["", ""],
                 ["Data i podpis opiekuna uczelnianego:", ""]]
    sig2 = Table(sig2_data, colWidths=[10*cm, 6.5*cm])
    sig2.setStyle(TableStyle([
        ("LINEABOVE",  (1, 1), (1, 1), 0.5, colors.black),
        ("FONTNAME",   (0, 0), (-1, -1), _FONT_NAME),
        ("FONTSIZE",   (0, 0), (-1, -1), 8),
    ]))
    elements.append(sig2)

    elements.extend(_footer_text(styles))

    doc.build(elements)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────────────
# 2. Dziennik praktyki zawodowej
# ─────────────────────────────────────────────────────────────────────────────

def generate_journal_pdf(data: dict) -> io.BytesIO:
    """
    Generuje PDF dziennika praktyki.

    Parametry data:
      student_name, album, specialization, academic_year,
      practice_place, start_date, end_date, attachments,
      entries: list of {day, date, description, effects_numbers, supervisor}

    Odporność: None/puste pola zastępowane „–"; długie opisy skracane; brak wpisów = komunikat.
    """
    if not data:
        data = {}
    _register_fonts()
    styles = _get_styles()
    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )
    elements = []

    # ── Nagłówek ──────────────────────────────────────────────────────────────
    _header_block(elements,
                  "Dziennik praktyki zawodowej",
                  "Informatyka – praktyka kierunkowa",
                  styles)

    # ── Dane studenta ─────────────────────────────────────────────────────────
    elements.append(Paragraph("Dane studenta i praktyki", styles["section"]))
    info = [
        ["Student:",          _safe_str(data.get("student_name")),
         "Nr albumu:",        _safe_str(data.get("album"))],
        ["W zakresie:",       _safe_str(data.get("specialization")),
         "Rok akademicki:",   _safe_str(data.get("academic_year"))],
        ["Miejsce praktyki:", _safe_str(data.get("practice_place")),
         "Data rozpoczęcia:", _safe_str(data.get("start_date"))],
        ["",                  "",
         "Data zakończenia:", _safe_str(data.get("end_date"))],
    ]
    info_table = Table(info, colWidths=[3.5*cm, 7*cm, 3.5*cm, 3*cm])
    info_table.setStyle(TableStyle([
        ("FONTNAME",      (0, 0), (0, -1), _FONT_BOLD),
        ("FONTNAME",      (2, 0), (2, -1), _FONT_BOLD),
        ("FONTNAME",      (1, 0), (1, -1), _FONT_NAME),
        ("FONTNAME",      (3, 0), (3, -1), _FONT_NAME),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW",     (0, 0), (-1, -1), 0.3, colors.HexColor("#CCCCCC")),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.4*cm))

    # ── Tabela wpisów ─────────────────────────────────────────────────────────
    elements.append(Paragraph("Wpisy dziennika", styles["section"]))

    entries = data.get("entries") or []
    if not isinstance(entries, list):
        entries = []
    if entries:
        journal_data = [["Dzień", "Data", "Opis wykonanych prac",
                          "Nr efektów\nuczenia się", "Podpis"]]
        for e in (entries if isinstance(entries, list) else []):
            if not isinstance(e, dict):
                continue
            journal_data.append([
                _safe_str(e.get("day"), max_len=10),
                _safe_str(e.get("date"), max_len=20),
                _safe_para(e.get("description"), styles["normal"], max_len=800),
                _safe_str(e.get("effects_numbers"), max_len=50),
                _safe_str(e.get("supervisor"), max_len=60),
            ])

        j_table = Table(
            journal_data,
            colWidths=[1.2*cm, 2.4*cm, 9*cm, 2.2*cm, 2.2*cm],
            repeatRows=1,
        )
        ts = _table_style_default()
        ts.add("ALIGN", (0, 0), (1, -1), "CENTER")
        ts.add("ALIGN", (3, 0), (4, -1), "CENTER")
        j_table.setStyle(ts)
        elements.append(j_table)
    else:
        elements.append(Paragraph("Brak wpisów dziennika.", styles["normal"]))

    elements.append(Spacer(1, 0.4*cm))

    # ── Załączniki ────────────────────────────────────────────────────────────
    attachments = data.get("attachments", "").strip()
    if attachments:
        elements.append(Paragraph("Wykaz załączników", styles["section"]))
        elements.append(Paragraph(attachments, styles["normal"]))
        elements.append(Spacer(1, 0.4*cm))

    # ── Linie podpisów ────────────────────────────────────────────────────────
    elements.append(Spacer(1, 0.5*cm))
    sig_data = [
        ["", "_" * 35, "", "_" * 35],
        ["", "Podpis studenta", "", "Podpis opiekuna zakładowego"],
    ]
    sig_table = Table(sig_data, colWidths=[1*cm, 8*cm, 1*cm, 8*cm])
    sig_table.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (-1, -1), _FONT_NAME),
        ("FONTSIZE",  (0, 0), (-1, -1), 8),
        ("ALIGN",     (1, 0), (1, -1), "CENTER"),
        ("ALIGN",     (3, 0), (3, -1), "CENTER"),
        ("TOPPADDING",(0, 1), (-1, -1), 2),
    ]))
    elements.append(sig_table)

    elements.extend(_footer_text(styles))

    doc.build(elements)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────────────
# 3. Raport końcowy (oba dokumenty w jednym PDF)
# ─────────────────────────────────────────────────────────────────────────────

def generate_report_pdf(confirmation_data: dict | None,
                        journal_data: dict | None) -> io.BytesIO:
    """
    Generuje zbiorczy PDF raportu końcowego zawierający:
      - stronę tytułową
      - potwierdzenie efektów uczenia się
      - dziennik praktyki

    Parametry:
      confirmation_data – dane z pliku effects_confirmation.json
      journal_data      – dane z pliku practice_journal.json
      (każdy może być None – sekcja zostanie pominięta)
    """
    _register_fonts()
    styles = _get_styles()
    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )
    elements = []

    # ── Strona tytułowa ───────────────────────────────────────────────────────
    elements.append(Spacer(1, 3*cm))
    elements.append(Paragraph("Akademia Nauk Stosowanych w Elblągu", styles["subtitle"]))
    elements.append(Spacer(1, 0.5*cm))
    elements.append(Paragraph("RAPORT KOŃCOWY PRAKTYKI ZAWODOWEJ", styles["title"]))
    elements.append(Spacer(1, 0.5*cm))
    elements.append(Paragraph("Informatyka – praktyka kierunkowa", styles["subtitle"]))
    elements.append(Spacer(1, 1*cm))
    elements.append(HRFlowable(width="60%", thickness=1.5,
                                color=colors.HexColor("#2E5FA3"),
                                spaceAfter=12, hAlign="CENTER"))
    elements.append(Spacer(1, 1*cm))

    # Dane z dostępnych dokumentów
    student_name = "–"
    album        = "–"
    if journal_data:
        student_name = journal_data.get("student_name", "–")
        album        = journal_data.get("album", "–")
    elif confirmation_data:
        student_name = confirmation_data.get("student_name", "–")
        album        = confirmation_data.get("album", "–")

    cover_data = [
        ["Student:", student_name],
        ["Nr albumu:", album],
        ["Data raportu:", date.today().strftime("%d.%m.%Y")],
    ]
    cover_table = Table(cover_data, colWidths=[5*cm, 11*cm])
    cover_table.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (0, -1), _FONT_BOLD),
        ("FONTNAME",  (1, 0), (1, -1), _FONT_NAME),
        ("FONTSIZE",  (0, 0), (-1, -1), 11),
        ("TOPPADDING",(0, 0), (-1, -1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1),8),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#CCCCCC")),
        ("ALIGN",     (0, 0), (-1, -1), "LEFT"),
    ]))
    elements.append(cover_table)
    elements.append(Spacer(1, 2*cm))

    spis = [
        ["Spis treści:"],
        ["1. Potwierdzenie efektów uczenia się (Załącznik nr 4)"],
        ["2. Dziennik praktyki zawodowej"],
    ]
    spis_table = Table(spis, colWidths=[16.5*cm])
    spis_table.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (0, 0), _FONT_BOLD),
        ("FONTNAME",  (0, 1), (0, -1), _FONT_NAME),
        ("FONTSIZE",  (0, 0), (-1, -1), 10),
        ("TOPPADDING",(0, 0), (-1, -1), 5),
        ("LEFTPADDING",(0,1),(-1,-1), 15),
    ]))
    elements.append(spis_table)

    # ── Część 1: Potwierdzenie efektów ───────────────────────────────────────
    elements.append(PageBreak())
    _header_block(elements,
                  "Część 1: Potwierdzenie efektów uczenia się",
                  "Załącznik nr 4",
                  styles)

    if confirmation_data:
        # Dane studenta
        elements.append(Paragraph("Dane studenta", styles["section"]))
        sd = [
            ["Student/ka:", confirmation_data.get("student_name", "–"),
             "Nr albumu:", confirmation_data.get("album", "–")],
            ["Specjalność:", confirmation_data.get("specialty", "–"),
             "Liczba godzin:", str(confirmation_data.get("hours", "–"))],
        ]
        st = Table(sd, colWidths=[3.5*cm, 7*cm, 3*cm, 3*cm])
        st.setStyle(TableStyle([
            ("FONTNAME",  (0,0),(0,-1), _FONT_BOLD),
            ("FONTNAME",  (2,0),(2,-1), _FONT_BOLD),
            ("FONTNAME",  (1,0),(1,-1), _FONT_NAME),
            ("FONTNAME",  (3,0),(3,-1), _FONT_NAME),
            ("FONTSIZE",  (0,0),(-1,-1), 9),
            ("LINEBELOW", (0,0),(-1,-1), 0.3, colors.HexColor("#CCCCCC")),
            ("TOPPADDING",(0,0),(-1,-1), 4),
            ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ]))
        elements.append(st)
        elements.append(Spacer(1, 0.4*cm))

        # Tabela efektów
        effects = confirmation_data.get("effects", {})
        table_data = [["Nr", "Opis efektu uczenia się", "Uzyskano"]]
        for nr, opis in EFFECTS_LIST:
            achieved = effects.get(nr, False)
            table_data.append([nr, Paragraph(opis, styles["normal"]),
                                "✓" if achieved else "–"])
        eff_table = Table(table_data, colWidths=[1*cm, 13.5*cm, 2*cm])
        ts = _table_style_default()
        ts.add("ALIGN", (0, 0), (0, -1), "CENTER")
        ts.add("ALIGN", (2, 0), (2, -1), "CENTER")
        for i, (nr, _) in enumerate(EFFECTS_LIST, start=1):
            if effects.get(nr, False):
                ts.add("TEXTCOLOR", (2, i), (2, i), colors.HexColor("#16a34a"))
                ts.add("FONTNAME",  (2, i), (2, i), _FONT_BOLD)
        eff_table.setStyle(ts)
        elements.append(eff_table)
    else:
        elements.append(Paragraph("Brak danych potwierdzenia efektów.", styles["normal"]))

    # ── Część 2: Dziennik ─────────────────────────────────────────────────────
    elements.append(PageBreak())
    _header_block(elements,
                  "Część 2: Dziennik praktyki zawodowej",
                  "",
                  styles)

    if journal_data:
        entries = journal_data.get("entries", [])
        if entries:
            journal_rows = [["Dzień", "Data", "Opis wykonanych prac",
                              "Nr efektów", "Podpis"]]
            for e in entries:
                journal_rows.append([
                    e.get("day", ""),
                    e.get("date", ""),
                    Paragraph(e.get("description", ""), styles["normal"]),
                    e.get("effects_numbers", ""),
                    e.get("supervisor", ""),
                ])
            jt = Table(journal_rows,
                       colWidths=[1.2*cm, 2.4*cm, 9*cm, 2.2*cm, 2.2*cm],
                       repeatRows=1)
            ts2 = _table_style_default()
            ts2.add("ALIGN", (0, 0), (1, -1), "CENTER")
            ts2.add("ALIGN", (3, 0), (4, -1), "CENTER")
            jt.setStyle(ts2)
            elements.append(jt)
        else:
            elements.append(Paragraph("Brak wpisów dziennika.", styles["normal"]))
    else:
        elements.append(Paragraph("Brak danych dziennika.", styles["normal"]))

    elements.extend(_footer_text(styles))

    doc.build(elements)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────────────
# 4. Karta praktyki zawodowej (Załącznik nr 3)
# ─────────────────────────────────────────────────────────────────────────────

def generate_card_pdf(data: dict) -> io.BytesIO:
    """Generuje PDF karty praktyki zawodowej (Załącznik nr 3)."""
    if not data:
        data = {}
    _register_fonts()
    styles = _get_styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    elements = []

    _header_block(elements, "Karta praktyki zawodowej",
                  "Załącznik nr 3 – praktyka zawodowa studentów informatyki", styles)

    elements.append(Paragraph("Dane studenta", styles["section"]))
    sd = [
        ["Student/ka:", _safe_str(data.get("student_name")),
         "Nr albumu:", _safe_str(data.get("album"))],
        ["Kierunek:", _safe_str(data.get("study_program")),
         "Specjalność:", _safe_str(data.get("specialization"))],
        ["Rok akademicki:", _safe_str(data.get("academic_year")),
         "Semestr:", _safe_str(data.get("semester"))],
    ]
    _tbl = Table(sd, colWidths=[3.5*cm, 7*cm, 3*cm, 3*cm])
    _tbl.setStyle(TableStyle([
        ("FONTNAME",      (0, 0), (0, -1), _FONT_BOLD),
        ("FONTNAME",      (2, 0), (2, -1), _FONT_BOLD),
        ("FONTNAME",      (1, 0), (1, -1), _FONT_NAME),
        ("FONTNAME",      (3, 0), (3, -1), _FONT_NAME),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("LINEBELOW",     (0, 0), (-1, -1), 0.3, colors.HexColor("#CCCCCC")),
    ]))
    elements.append(_tbl)
    elements.append(Spacer(1, 0.4*cm))

    elements.append(Paragraph("Dane zakładu pracy", styles["section"]))
    cd = [
        ["Nazwa firmy:", _safe_str(data.get("company_name")), "", ""],
        ["Adres:", _safe_str(data.get("company_address")), "", ""],
        ["Telefon:", _safe_str(data.get("company_phone")),
         "NIP:", _safe_str(data.get("company_nip"))],
        ["Profil działalności:", _safe_str(data.get("company_type")), "", ""],
    ]
    ct = Table(cd, colWidths=[3.5*cm, 7*cm, 3*cm, 3*cm])
    ct.setStyle(TableStyle([
        ("FONTNAME",      (0, 0), (0, -1), _FONT_BOLD),
        ("FONTNAME",      (2, 0), (2, -1), _FONT_BOLD),
        ("FONTNAME",      (1, 0), (1, -1), _FONT_NAME),
        ("FONTNAME",      (3, 0), (3, -1), _FONT_NAME),
        ("SPAN",          (1, 0), (3, 0)),
        ("SPAN",          (1, 1), (3, 1)),
        ("SPAN",          (1, 3), (3, 3)),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("LINEBELOW",     (0, 0), (-1, -1), 0.3, colors.HexColor("#CCCCCC")),
    ]))
    elements.append(ct)
    elements.append(Spacer(1, 0.4*cm))

    elements.append(Paragraph("Opiekun zakładowy i przebieg praktyki", styles["section"]))
    pd = [
        ["Opiekun zakładowy:", _safe_str(data.get("company_supervisor_name")),
         "Stanowisko:", _safe_str(data.get("company_supervisor_title"))],
        ["Opiekun uczelniany:", _safe_str(data.get("university_supervisor")), "", ""],
        ["Rozpoczęcie:", _safe_str(data.get("start_date")),
         "Zakończenie:", _safe_str(data.get("end_date"))],
        ["Łączna liczba godzin:", _safe_str(data.get("total_hours")),
         "Ocena:", _safe_str(data.get("grade"))],
    ]
    pt = Table(pd, colWidths=[3.5*cm, 7*cm, 3*cm, 3*cm])
    pt.setStyle(TableStyle([
        ("FONTNAME",      (0, 0), (0, -1), _FONT_BOLD),
        ("FONTNAME",      (2, 0), (2, -1), _FONT_BOLD),
        ("FONTNAME",      (1, 0), (1, -1), _FONT_NAME),
        ("FONTNAME",      (3, 0), (3, -1), _FONT_NAME),
        ("SPAN",          (1, 1), (3, 1)),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("LINEBELOW",     (0, 0), (-1, -1), 0.3, colors.HexColor("#CCCCCC")),
    ]))
    elements.append(pt)
    elements.append(Spacer(1, 0.4*cm))

    elements.append(Paragraph("Opinia opiekuna zakładowego", styles["section"]))
    elements.append(Paragraph(
        _safe_str(data.get("company_supervisor_opinion"), default="Brak opinii.", max_len=1000),
        styles["justify"]
    ))
    elements.append(Spacer(1, 0.5*cm))

    sig_data = [
        ["Pieczęć zakładu pracy:", "", "Podpis opiekuna zakładowego:", ""],
        ["", "", "", ""],
        ["", "", "", ""],
    ]
    sig = Table(sig_data, colWidths=[4.5*cm, 4*cm, 4.5*cm, 3.5*cm])
    sig.setStyle(TableStyle([
        ("FONTNAME",      (0, 0), (-1, -1), _FONT_NAME),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("LINEBELOW",     (1, 2), (1, 2), 0.5, colors.black),
        ("LINEBELOW",     (3, 2), (3, 2), 0.5, colors.black),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    elements.append(sig)

    elements.extend(_footer_text(styles))
    doc.build(elements)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────────────
# 5. Kwestionariusz ankiety (Załącznik nr 5)
# ─────────────────────────────────────────────────────────────────────────────

_SURVEY_QUESTIONS = [
    ("q1",  "Organizacja i przygotowanie miejsca praktyki"),
    ("q2",  "Zgodność zadań z kierunkiem / specjalnością studiów"),
    ("q3",  "Dostęp do sprzętu i oprogramowania"),
    ("q4",  "Dostępność i pomoc opiekuna zakładowego"),
    ("q5",  "Możliwość samodzielnego działania i podejmowania decyzji"),
    ("q6",  "Atmosfera w miejscu pracy"),
    ("q7",  "Stopień przygotowania uczelni do praktyk (program, dokumentacja)"),
    ("q8",  "Przydatność wiedzy zdobytej na uczelni w praktyce"),
    ("q9",  "Możliwość nabycia nowych kompetencji i umiejętności"),
    ("q10", "Ogólna ocena praktyki"),
]


def generate_survey_pdf(data: dict) -> io.BytesIO:
    """Generuje PDF kwestionariusza ankiety (Załącznik nr 5)."""
    if not data:
        data = {}
    _register_fonts()
    styles = _get_styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    elements = []

    _header_block(elements, "Kwestionariusz ankiety",
                  "Załącznik nr 5 – ocena jakości praktyki zawodowej", styles)

    elements.append(Paragraph("Dane studenta", styles["section"]))
    sd = [
        ["Student/ka:", _safe_str(data.get("student_name")),
         "Nr albumu:", _safe_str(data.get("album"))],
        ["Rok akademicki:", _safe_str(data.get("academic_year")),
         "Firma:", _safe_str(data.get("company_name"))],
    ]
    st = Table(sd, colWidths=[3.5*cm, 7*cm, 3*cm, 3*cm])
    st.setStyle(TableStyle([
        ("FONTNAME",      (0, 0), (0, -1), _FONT_BOLD),
        ("FONTNAME",      (2, 0), (2, -1), _FONT_BOLD),
        ("FONTNAME",      (1, 0), (1, -1), _FONT_NAME),
        ("FONTNAME",      (3, 0), (3, -1), _FONT_NAME),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("LINEBELOW",     (0, 0), (-1, -1), 0.3, colors.HexColor("#CCCCCC")),
    ]))
    elements.append(st)
    elements.append(Spacer(1, 0.4*cm))

    elements.append(Paragraph("Ocena praktyki (skala 1–5)", styles["section"]))
    elements.append(Paragraph(
        "1 – bardzo źle,  2 – źle,  3 – dostatecznie,  4 – dobrze,  5 – bardzo dobrze",
        styles["normal"]
    ))
    elements.append(Spacer(1, 0.2*cm))

    sq_data = [["Nr", "Kryterium oceny", "Ocena"]]
    for i, (key, question) in enumerate(_SURVEY_QUESTIONS, start=1):
        val = str(data.get(key, "–")) if data.get(key) else "–"
        sq_data.append([str(i), Paragraph(question, styles["normal"]), val])

    sq = Table(sq_data, colWidths=[1*cm, 13.5*cm, 2*cm])
    ts = _table_style_default()
    ts.add("ALIGN", (0, 0), (0, -1), "CENTER")
    ts.add("ALIGN", (2, 0), (2, -1), "CENTER")
    for i, (key, _) in enumerate(_SURVEY_QUESTIONS, start=1):
        try:
            v = int(data.get(key, 0))
            if v >= 4:
                ts.add("TEXTCOLOR", (2, i), (2, i), colors.HexColor("#16a34a"))
                ts.add("FONTNAME",  (2, i), (2, i), _FONT_BOLD)
        except (ValueError, TypeError):
            pass
    sq.setStyle(ts)
    elements.append(sq)
    elements.append(Spacer(1, 0.4*cm))

    elements.append(Paragraph("Pytania otwarte", styles["section"]))
    open_q = [
        ("Co było najbardziej wartościowe podczas praktyki?", "most_valuable"),
        ("Co należałoby poprawić?", "improvements"),
        ("Czy polecasz to miejsce praktyki?", "recommend"),
        ("Dodatkowe uwagi i komentarze:", "comments"),
    ]
    for label, key in open_q:
        elements.append(Paragraph(label, styles["label"]))
        elements.append(Paragraph(
            _safe_str(data.get(key), default="Brak odpowiedzi.", max_len=500),
            styles["justify"]
        ))
        elements.append(Spacer(1, 0.3*cm))

    elements.extend(_footer_text(styles))
    doc.build(elements)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────────────
# 6. Sprawozdanie z praktyki zawodowej (Załącznik nr 7)
# ─────────────────────────────────────────────────────────────────────────────

def generate_report7_pdf(data: dict) -> io.BytesIO:
    """Generuje PDF sprawozdania z praktyki zawodowej (Załącznik nr 7)."""
    if not data:
        data = {}
    _register_fonts()
    styles = _get_styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    elements = []

    _header_block(elements, "Sprawozdanie z praktyki zawodowej",
                  "Załącznik nr 7 – końcowe sprawozdanie studenta", styles)

    elements.append(Paragraph("Dane studenta i zakładu pracy", styles["section"]))
    sd = [
        ["Student/ka:", _safe_str(data.get("student_name")),
         "Nr albumu:", _safe_str(data.get("album"))],
        ["Specjalność:", _safe_str(data.get("specialization")),
         "Rok akademicki:", _safe_str(data.get("academic_year"))],
        ["Firma:", _safe_str(data.get("company_name")),
         "Adres:", _safe_str(data.get("company_address"))],
        ["Rozpoczęcie:", _safe_str(data.get("start_date")),
         "Zakończenie:", _safe_str(data.get("end_date"))],
    ]
    st = Table(sd, colWidths=[3.5*cm, 7*cm, 3*cm, 3*cm])
    st.setStyle(TableStyle([
        ("FONTNAME",      (0, 0), (0, -1), _FONT_BOLD),
        ("FONTNAME",      (2, 0), (2, -1), _FONT_BOLD),
        ("FONTNAME",      (1, 0), (1, -1), _FONT_NAME),
        ("FONTNAME",      (3, 0), (3, -1), _FONT_NAME),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("LINEBELOW",     (0, 0), (-1, -1), 0.3, colors.HexColor("#CCCCCC")),
    ]))
    elements.append(st)
    elements.append(Spacer(1, 0.4*cm))

    for title, key in [
        ("Charakterystyka zakładu pracy",                "company_description"),
        ("Dział / zespół",                               "department"),
        ("Wykonywane zadania i prace",                   "tasks_description"),
        ("Zastosowane technologie i narzędzia",          "technologies"),
        ("Udział w projektach",                          "projects"),
        ("Napotkane trudności i sposób ich rozwiązania", "problems"),
        ("Wnioski końcowe",                              "conclusions"),
    ]:
        elements.append(Paragraph(title, styles["section"]))
        elements.append(Paragraph(
            _safe_str(data.get(key), default="Brak opisu.", max_len=2000),
            styles["justify"]
        ))
        elements.append(Spacer(1, 0.3*cm))

    elements.append(Paragraph("Samoocena efektów uczenia się", styles["section"]))
    self_effects = data.get("self_effects") or {}
    if not isinstance(self_effects, dict):
        self_effects = {}

    eff_data = [["Nr", "Opis efektu uczenia się", "Osiągnięty"]]
    for nr, opis in EFFECTS_LIST:
        achieved = bool(self_effects.get(nr, False))
        eff_data.append([nr, Paragraph(opis, styles["normal"]), "✓" if achieved else "–"])

    eff_t = Table(eff_data, colWidths=[1*cm, 13.5*cm, 2*cm])
    ts2 = _table_style_default()
    ts2.add("ALIGN", (0, 0), (0, -1), "CENTER")
    ts2.add("ALIGN", (2, 0), (2, -1), "CENTER")
    for i, (nr, _) in enumerate(EFFECTS_LIST, start=1):
        if self_effects.get(nr, False):
            ts2.add("TEXTCOLOR", (2, i), (2, i), colors.HexColor("#16a34a"))
            ts2.add("FONTNAME",  (2, i), (2, i), _FONT_BOLD)
    eff_t.setStyle(ts2)
    elements.append(eff_t)
    elements.append(Spacer(1, 0.5*cm))

    sig_data = [["", ""], ["Data i podpis studenta:", ""]]
    sig = Table(sig_data, colWidths=[10*cm, 6.5*cm])
    sig.setStyle(TableStyle([
        ("LINEABOVE", (1, 1), (1, 1), 0.5, colors.black),
        ("FONTNAME",  (0, 0), (-1, -1), _FONT_NAME),
        ("FONTSIZE",  (0, 0), (-1, -1), 8),
    ]))
    elements.append(sig)

    elements.extend(_footer_text(styles))
    doc.build(elements)
    buf.seek(0)
    return buf
