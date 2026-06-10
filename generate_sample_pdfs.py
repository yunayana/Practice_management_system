"""
Skrypt generujący przykładowe pliki PDF dla celów testowych (Etap 11A, Zadanie 7).

Uruchomienie:
    cd Practice_management_system
    python generate_sample_pdfs.py

Wynik:
    sample_pdfs/
      potwierdzenie_101.pdf   – kompletne dane
      potwierdzenie_102.pdf   – częściowe dane (brak notek)
      potwierdzenie_103.pdf   – dane z polskimi znakami i długimi tekstami
      dziennik_201.pdf        – kompletny dziennik (5 wpisów)
      dziennik_202.pdf        – pusty dziennik (0 wpisów)
      dziennik_203.pdf        – dziennik z uszkodzonymi wpisami (None, brak kluczy)
      raport_301.pdf          – pełny raport (potwierdzenie + dziennik)
      raport_302.pdf          – raport tylko z potwierdzeniem
      raport_303.pdf          – raport tylko z dziennikiem
"""
from __future__ import annotations

import os
import sys

# Upewnij się, że importy działają bez uruchamiania Flask
sys.path.insert(0, os.path.dirname(__file__))

from pdf_generator import (
    generate_confirmation_pdf,
    generate_journal_pdf,
    generate_report_pdf,
)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "sample_pdfs")


# ─────────────────────────────────────────────────────────────────────────────
# Dane testowe
# ─────────────────────────────────────────────────────────────────────────────

# Potwierdzenia ────────────────────────────────────────────────────────────────

CONF_101 = {
    "student_name": "Anna Kowalska",
    "album": "101",
    "specialty": "Informatyka stosowana",
    "hours": "160",
    "effects": {f"{i:02d}": (i % 3 != 0) for i in range(1, 14)},
    "company_supervisor_note": (
        "Studentka wykazała się wysokimi kompetencjami technicznymi. "
        "Aktywnie uczestniczyła w projektach zespołu deweloperskiego."
    ),
    "university_supervisor_opinion": (
        "Praktykantka spełniła wszystkie wymagania programowe. Ocena bardzo dobra."
    ),
}

CONF_102 = {
    "student_name": "Piotr Nowak",
    "album": "102",
    "specialty": "Zarządzanie i inżynieria produkcji",
    "hours": "120",
    "effects": {f"{i:02d}": True for i in range(1, 14)},
    # Brak notek opiekunów – test obsługi pustych pól
    "company_supervisor_note": "",
    "university_supervisor_opinion": None,
}

CONF_103 = {
    "student_name": "Józef Święcicki-Błaszczyk",
    "album": "103",
    "specialty": "Automatyka i robotyka – specjalizacja: Systemy wbudowane",
    "hours": "240",
    "effects": {f"{i:02d}": True for i in range(1, 14)},
    "company_supervisor_note": (
        "Żółw łączy żółte źródła żywiczne. " * 15  # długi tekst – test obcięcia
    ),
    "university_supervisor_opinion": (
        "Ćwiczył się w zadaniach z dziedziny automatyki przemysłowej. "
        "Wykazał się inicjatywą i sumiennością. Oceniam praktykę na ocenę bardzo dobrą."
    ),
}

# Dzienniki ────────────────────────────────────────────────────────────────────

JOUR_201 = {
    "student_name": "Anna Kowalska",
    "album": "201",
    "specialization": "Informatyka stosowana",
    "academic_year": "2024/2025",
    "practice_place": "Firma Technologiczna XYZ Sp. z o.o., ul. Lipowa 5, Elbląg",
    "start_date": "2025-07-01",
    "end_date": "2025-07-28",
    "attachments": "Zaświadczenie z firmy, dziennik w formie papierowej",
    "entries": [
        {
            "day": "1",
            "date": "2025-07-01",
            "description": "Zapoznanie z firmą, stanowiskiem pracy oraz regulaminem BHP.",
            "effects_numbers": "01, 02",
            "supervisor": "mgr Jan Wiśniewski",
        },
        {
            "day": "2",
            "date": "2025-07-02",
            "description": "Konfiguracja środowiska programistycznego (Python, Git, Docker).",
            "effects_numbers": "03, 04",
            "supervisor": "mgr Jan Wiśniewski",
        },
        {
            "day": "3",
            "date": "2025-07-03",
            "description": "Uczestnictwo w spotkaniu scrum. Przypisanie pierwszych zadań.",
            "effects_numbers": "05, 06",
            "supervisor": "mgr Jan Wiśniewski",
        },
        {
            "day": "4",
            "date": "2025-07-04",
            "description": "Implementacja modułu autoryzacji użytkowników (JWT).",
            "effects_numbers": "07, 08",
            "supervisor": "mgr Alicja Marek",
        },
        {
            "day": "5",
            "date": "2025-07-07",
            "description": "Testy jednostkowe i code review. Poprawki po uwagach mentora.",
            "effects_numbers": "09, 10, 11",
            "supervisor": "mgr Alicja Marek",
        },
    ],
}

JOUR_202 = {
    "student_name": "Tomasz Zając",
    "album": "202",
    "specialization": "Budownictwo",
    "academic_year": "2024/2025",
    "practice_place": "Przedsiębiorstwo Budowlane ABC",
    "start_date": "2025-06-02",
    "end_date": "2025-06-27",
    "attachments": "",
    "entries": [],  # pusty dziennik
}

JOUR_203 = {
    "student_name": "Maria Dąbrowska",
    "album": "203",
    "specialization": None,         # brak specjalizacji
    "academic_year": "2023/2024",
    "practice_place": "Urząd Miejski w Elblągu",
    "start_date": "",               # brak daty
    "end_date": "2024-08-30",
    "attachments": "Sprawozdanie końcowe",
    "entries": [
        {
            "day": "1",
            "date": "2024-07-01",
            "description": "Zapoznanie z zakresem obowiązków.",
            "effects_numbers": "01",
            "supervisor": "Dyrektor Wydziału",
        },
        None,                        # uszkodzony wpis – test odporności
        {
            "day": "3",
            # brak klucza "date" – test brakujących kluczy
            "description": "Obsługa klientów w okienku podawczym.",
            "effects_numbers": "02, 03",
            "supervisor": "",
        },
        "to nie jest słownik",       # wpis jako string – test odporności
    ],
}

# Dane łączone dla raportów ───────────────────────────────────────────────────

CONF_FOR_301 = {**CONF_101, "album": "301"}
JOUR_FOR_301 = {**JOUR_201, "album": "301"}

CONF_FOR_302 = {**CONF_102, "album": "302"}

JOUR_FOR_303 = {**JOUR_203, "album": "303"}


# ─────────────────────────────────────────────────────────────────────────────
# Generowanie
# ─────────────────────────────────────────────────────────────────────────────

def save(buf, filename: str) -> None:
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "wb") as f:
        f.write(buf.read())
    size_kb = os.path.getsize(path) / 1024
    print(f"  ✓  {filename:45s}  ({size_kb:.1f} KB)")


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"\nGenerowanie przykładowych PDF → {OUTPUT_DIR}\n")

    errors: list[str] = []

    tasks = [
        # (funkcja, argumenty, nazwa_pliku, opis)
        (generate_confirmation_pdf, (CONF_101,), "potwierdzenie_101.pdf",
         "Potwierdzenie – kompletne dane"),
        (generate_confirmation_pdf, (CONF_102,), "potwierdzenie_102.pdf",
         "Potwierdzenie – puste pola opiekunów"),
        (generate_confirmation_pdf, (CONF_103,), "potwierdzenie_103.pdf",
         "Potwierdzenie – polskie znaki, długie teksty"),

        (generate_journal_pdf, (JOUR_201,), "dziennik_201.pdf",
         "Dziennik – 5 kompletnych wpisów"),
        (generate_journal_pdf, (JOUR_202,), "dziennik_202.pdf",
         "Dziennik – 0 wpisów (pusty)"),
        (generate_journal_pdf, (JOUR_203,), "dziennik_203.pdf",
         "Dziennik – uszkodzone wpisy, None-y"),

        (generate_report_pdf, (CONF_FOR_301, JOUR_FOR_301), "raport_301.pdf",
         "Raport – pełny (oba dokumenty)"),
        (generate_report_pdf, (CONF_FOR_302, None), "raport_302.pdf",
         "Raport – tylko potwierdzenie"),
        (generate_report_pdf, (None, JOUR_FOR_303), "raport_303.pdf",
         "Raport – tylko dziennik"),
    ]

    for func, args, filename, desc in tasks:
        print(f"  → {desc}")
        try:
            buf = func(*args)
            save(buf, filename)
        except Exception as exc:
            print(f"  ✗  BŁĄD: {exc}")
            errors.append(f"{filename}: {exc}")

    print(f"\nGotowe. Wygenerowano {len(tasks) - len(errors)}/{len(tasks)} plików.")
    if errors:
        print("\nBłędy:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("Wszystkie pliki wygenerowane pomyślnie.\n")


if __name__ == "__main__":
    main()
