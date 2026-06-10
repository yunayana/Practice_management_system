-- ============================================================
-- Szkielet bazy danych: Aplikacja do obsługi praktyk zawodowych
-- Silnik: SQLite (kompatybilny z MySQL/MariaDB po drobnych zmianach)
-- ============================================================

-- Tabela użytkowników systemu (wspólna dla wszystkich ról)
CREATE TABLE users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name   TEXT    NOT NULL,
    email       TEXT    NOT NULL UNIQUE,
    password_hash TEXT  NOT NULL,
    role        TEXT    NOT NULL CHECK (role IN ('student', 'uczelniany', 'zakladowy', 'sekretariat')),
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Profil studenta (rozszerza users)
CREATE TABLE students (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL UNIQUE,
    album           TEXT    NOT NULL UNIQUE,       -- numer albumu
    specialization  TEXT    NOT NULL,
    academic_year   TEXT    NOT NULL,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Profil opiekuna (rozszerza users)
CREATE TABLE supervisors (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL UNIQUE,
    supervisor_type TEXT    NOT NULL CHECK (supervisor_type IN ('uczelniany', 'zakladowy', 'sekretariat')),
    department      TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Praktyka zawodowa (główna encja dokumentu)
CREATE TABLE practices (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id                  INTEGER NOT NULL,
    company_name                TEXT    NOT NULL,
    start_date                  TEXT    NOT NULL,
    end_date                    TEXT    NOT NULL,
    hours                       INTEGER,
    status                      TEXT    NOT NULL DEFAULT 'Draft'
                                    CHECK (status IN ('Draft','Submitted','Under_Review','Rejected','Approved','Closed')),
    university_supervisor_id    INTEGER,           -- opiekun uczelniany
    company_supervisor_id       INTEGER,           -- opiekun zakładowy
    grade                       TEXT,              -- ocena końcowa
    attachments_notes           TEXT,
    created_at                  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at                  TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (student_id)                REFERENCES students(id),
    FOREIGN KEY (university_supervisor_id)  REFERENCES supervisors(id),
    FOREIGN KEY (company_supervisor_id)     REFERENCES supervisors(id)
);

-- Dziennik praktyki (relacja 1:1 z practices)
CREATE TABLE practice_journals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    practice_id INTEGER NOT NULL UNIQUE,
    status      TEXT    NOT NULL DEFAULT 'Draft'
                    CHECK (status IN ('Draft','Submitted','Under_Review','Rejected','Approved','Closed')),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (practice_id) REFERENCES practices(id)
);

-- Wpisy dziennika (relacja 1:N z practice_journals)
CREATE TABLE journal_entries (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    journal_id          INTEGER NOT NULL,
    day_number          INTEGER NOT NULL,
    entry_date          TEXT    NOT NULL,
    description         TEXT    NOT NULL,
    effects_numbers     TEXT,              -- np. "1,3,5"
    supervisor_signature TEXT,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (journal_id) REFERENCES practice_journals(id)
);

-- Efekty uczenia się (słownik, 13 pozycji)
CREATE TABLE learning_effects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT    NOT NULL UNIQUE,   -- np. "01", "02", ..., "13"
    description TEXT    NOT NULL
);

-- Potwierdzenie efektów uczenia (relacja 1:1 z practices)
CREATE TABLE effects_confirmations (
    id                              INTEGER PRIMARY KEY AUTOINCREMENT,
    practice_id                     INTEGER NOT NULL UNIQUE,
    company_supervisor_note         TEXT,
    university_supervisor_opinion   TEXT,
    status                          TEXT    NOT NULL DEFAULT 'Draft'
                                        CHECK (status IN ('Draft','Submitted','Under_Review','Rejected','Approved')),
    created_at                      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at                      TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (practice_id) REFERENCES practices(id)
);

-- Encja pośrednia N:M: potwierdzenie <-> efekty uczenia się
CREATE TABLE effects_confirmation_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    confirmation_id INTEGER NOT NULL,
    effect_id       INTEGER NOT NULL,
    confirmed       INTEGER NOT NULL DEFAULT 0 CHECK (confirmed IN (0, 1)),
    UNIQUE (confirmation_id, effect_id),
    FOREIGN KEY (confirmation_id) REFERENCES effects_confirmations(id),
    FOREIGN KEY (effect_id)       REFERENCES learning_effects(id)
);

-- Uwagi opiekuna do dokumentów
CREATE TABLE supervisor_comments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    practice_id     INTEGER NOT NULL,
    supervisor_id   INTEGER NOT NULL,
    document_type   TEXT    NOT NULL CHECK (document_type IN ('journal','effects_confirmation')),
    content         TEXT    NOT NULL,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (practice_id)   REFERENCES practices(id),
    FOREIGN KEY (supervisor_id) REFERENCES supervisors(id)
);

-- ============================================================
-- Dane słownikowe: efekty uczenia się (01–13)
-- ============================================================
INSERT INTO learning_effects (code, description) VALUES
    ('01', 'Potrafi zastosować wiedzę teoretyczną w praktyce zawodowej'),
    ('02', 'Rozumie procesy i procedury obowiązujące w miejscu praktyki'),
    ('03', 'Potrafi pracować samodzielnie i w zespole'),
    ('04', 'Stosuje zasady etyki zawodowej'),
    ('05', 'Potrafi identyfikować i rozwiązywać problemy techniczne'),
    ('06', 'Efektywnie komunikuje się z przełożonymi i współpracownikami'),
    ('07', 'Potrafi planować i organizować własną pracę'),
    ('08', 'Stosuje przepisy BHP i bezpieczeństwa informacji'),
    ('09', 'Potrafi dokumentować wykonane zadania'),
    ('10', 'Wykazuje inicjatywę i kreatywność'),
    ('11', 'Potrafi korzystać z narzędzi i technologii stosowanych w branży'),
    ('12', 'Rozumie strukturę organizacyjną przedsiębiorstwa'),
    ('13', 'Potrafi ocenić własne kompetencje i wskazać obszary rozwoju');
