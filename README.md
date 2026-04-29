# Practice_management_system

Projekt przedstawiający wymagania oraz modele logiki biznesowej aplikacji do obsługi praktyk zawodowych. System wspiera cyfrowy obieg dokumentacji praktyk, w tym tworzenie i edycję dziennika, przesyłanie dokumentów do weryfikacji, obsługę uwag opiekunów, zmianę statusów dokumentów, generowanie raportu PDF oraz archiwizację. 

## Funkcje systemu

- rejestracja danych studenta, 
- edycja i zapis dziennika praktyk, 
- wysyłanie dokumentów do weryfikacji, 
- dodawanie uwag i zmiana statusów, 
- wystawienie oceny końcowej i generowanie PDF,
- archiwizacja dokumentacji. 


## Cel

Celem projektu jest przedstawienie przepływu danych, interakcji użytkowników i logiki biznesowej aplikacji wspierającej cyfrową obsługę praktyk zawodowych. 

## Aktorzy systemu

W projekcie uwzględniono cztery główne role użytkowników systemu: studenta, opiekuna uczelnianego, opiekuna zakładowego oraz sekretariat lub dziekanat. Role te wynikają bezpośrednio z analizy wymagań systemu obsługi praktyk zawodowych. 

- **Student** – uzupełnia dokumentację praktyk, edytuje dziennik, wysyła dokumenty do weryfikacji i śledzi ich status. 
- **Opiekun uczelniany** – weryfikuje dokumenty, dodaje uwagi, odsyła je do poprawy albo zatwierdza, a także wystawia ocenę końcową i inicjuje generowanie PDF. 
- **Opiekun zakładowy** – może potwierdzać przebieg praktyki i dodawać uwagi do dokumentacji. 
- **Sekretariat / dziekanat** – odpowiada za końcową obsługę formalną i archiwizację zatwierdzonych dokumentów. 

## Diagram sekwencji – weryfikacja dziennika praktyk

Diagram sekwencji przedstawia proces przesłania dziennika do weryfikacji, walidację danych po stronie backendu, zapis zmian w bazie JSON oraz decyzję opiekuna uczelnianego o odrzuceniu lub zatwierdzeniu dokumentu. Taki model odpowiada wymaganiom zadania 1 z laboratorium 5. 

```mermaid
sequenceDiagram
    participant S as Student
    participant B as Backend Flask
    participant J as JSON Database
    participant O as Opiekun Uczelniany

    S ->> B: Wyslij dziennik do weryfikacji
    B ->> B: Walidacja danych i kompletnosci

    alt dane niekompletne lub niepoprawne
        B -->> S: Zwroc blad
    else dane poprawne
        B ->> J: Zapisz dokument i ustaw status Under_Review
        B ->> O: Powiadom o nowym dokumencie
        O ->> B: Sprawdz dokument

        alt Opiekun zglasza uwagi i odrzuca
            O ->> B: Dodaj uwagi i odrzuc dokument
            B ->> J: Zapisz uwagi i status Rejected
            B -->> S: Powiadom o koniecznosci poprawy
        else Opiekun zatwierdza dokument
            O ->> B: Zatwierdz dokument
            B ->> J: Ustaw status Approved
            B -->> S: Powiadom o zatwierdzeniu
        end
    end
```

## Diagram stanów – cykl życia dokumentu

Diagram stanów odwzorowuje cykl życia dokumentu praktyk od wersji roboczej do zamknięcia procesu. Uwzględnia on stany wymagane w treści laboratorium: Draft, Submitted, Under_Review, Rejected, Approved i Closed. 

```mermaid
stateDiagram-v2
    [*] --> Draft

    Draft --> Submitted: Wyslij do weryfikacji
    Submitted --> Under_Review: Odebrano przez system lub opiekuna

    Under_Review --> Approved: Zatwierdz dokument
    Under_Review --> Rejected: Odrzuc i dodaj uwagi

    Rejected --> Draft: Student wprowadza poprawki

    Approved --> Closed: Generowanie PDF i archiwizacja
    Closed --> [*]
```

Diagram pokazuje również powrót dokumentu do stanu Draft po odrzuceniu i zgłoszeniu uwag, co odpowiada workflow dokumentu opisanemu w wymaganiach projektu.

## Flowchart – logika uprawnień edycji

Ten flowchart odpowiada zadaniu 3 i pokazuje mechanizm kontroli dostępu podczas próby edycji dokumentu. Dokument może być edytowany wyłącznie przez zalogowanego studenta oraz tylko wtedy, gdy jego status to Draft lub Rejected. 

```mermaid
flowchart TD
    A[Proba edycji dokumentu] --> B{Uzytkownik zalogowany?}

    B -- Nie --> X[Wyswietl ekran logowania lub blad dostepu]
    B -- Tak --> C{Rola uzytkownika to Student?}

    C -- Nie --> Y[Wyswietl podglad dokumentu tylko do odczytu]
    C -- Tak --> D{Status dokumentu to Draft lub Rejected?}

    D -- Tak --> E[Udostepnij formularz edycji]
    D -- Nie --> Y[Wyswietl podglad dokumentu tylko do odczytu]
```

Model ten wynika z wymagania blokady edycji po wysłaniu dokumentu do weryfikacji oraz z rozróżnienia ról użytkowników i ich uprawnień.

## Flowchart – tworzenie i edycja dziennika

Ten scenariusz pokazuje podstawową ścieżkę pracy studenta z dokumentacją praktyk. Obejmuje logowanie, wejście do listy dokumentów, utworzenie nowego dziennika lub otwarcie istniejącego oraz zapis wersji roboczej. 

```mermaid
flowchart TD
    A[Start pracy z systemem] --> B[Logowanie studenta]
    B --> C[Wyswietl liste dokumentow praktyk]
    C --> D{Czy istnieje dziennik praktyk?}

    D -- Nie --> E[Utworz nowy dziennik]
    D -- Tak --> F[Otworz istniejacy dziennik]

    E --> G[Student edytuje wiersze dziennika]
    F --> G

    G --> H[Zapisz dokument jako wersje robocza Draft]
    H --> I[Powrot do listy dokumentow]
```

Diagram ten odpowiada funkcjom rejestracji danych studenta, edycji dziennika praktyk i powiązania dokumentów z użytkownikiem. 

## Flowchart – weryfikacja przez opiekuna

Ten diagram przedstawia proces przeglądu dokumentu przez opiekuna uczelnianego. Opiekun analizuje treść dokumentu i może albo zgłosić uwagi oraz odrzucić dokument, albo zatwierdzić go po pozytywnej weryfikacji. 

```mermaid
flowchart TD
    A[Opiekun uczelniany loguje sie] --> B[Lista dokumentow do weryfikacji]
    B --> C[Otworz dziennik w statusie Under_Review]
    C --> D[Przeglad wpisow dziennika i efektow uczenia sie]

    D --> E{Dokument poprawny?}

    E -- Nie --> F[Dodaj uwagi do sekcji]
    F --> G[Ustaw status Rejected lub do poprawy]
    G --> H[Zapisz dokument i powiadom studenta]
    H --> I[Student widzi status Rejected i uwagi]

    E -- Tak --> J[Ustaw status Approved]
    J --> K[Zapisz dokument]
```

Scenariusz ten odpowiada wymaganiom dotyczącym pracy na formularzu efektów uczenia się, dodawania uwag i zmiany statusu dokumentu. 

## Flowchart – poprawa po odrzuceniu

Po odrzuceniu dokumentu student może ponownie otworzyć dokument, przeanalizować uwagi opiekuna, wprowadzić poprawki i jeszcze raz wysłać dokument do sprawdzenia. Taki przebieg wynika bezpośrednio z opisanego workflow dziennika praktyk.

```mermaid
flowchart TD
    A[Student loguje sie] --> B[Otworz dziennik w statusie Rejected]
    B --> C[Wyswietl uwagi opiekuna]
    C --> D[Student wprowadza poprawki w dzienniku]
    D --> E[Zapisz zmiany jako Draft]
    E --> F[Student ponownie wybiera wyslij do weryfikacji]
    F --> G[Zmiana statusu na Submitted i blokada edycji]
```

Diagram pokazuje także, że status dokumentu ponownie przechodzi do etapu związanego z weryfikacją, a możliwość edycji zostaje ograniczona po wysłaniu dokumentu.

## Flowchart – finalizacja i archiwizacja

Końcowy etap procesu obejmuje zatwierdzenie dokumentacji, wystawienie oceny końcowej, wygenerowanie raportu PDF oraz przekazanie dokumentacji do archiwizacji. Taki przebieg odpowiada funkcjom F9, F10 i F12 z analizy wymagań. 

```mermaid
flowchart TD
    A[Opiekun otwiera dokument w statusie Approved] --> B[Wystaw ocene koncowa]
    B --> C[Zatwierdz proces praktyki]
    C --> D[Wygeneruj raport PDF z dokumentacji]
    D --> E[Przekaz dokumentacje do sekretariatu lub dziekanatu]
    E --> F[Archiwizacja dokumentu]
    F --> G[Status dokumentu Closed]
```

Diagram zamyka cały proces obsługi praktyk i odzwierciedla końcowy etap workflow dokumentu po pozytywnej weryfikacji przez opiekuna uczelnianego.

## Powiązanie z wymaganiami

Poniższa lista pokazuje, jak diagramy odnoszą się do wymagań funkcjonalnych systemu. Wymagania obejmują między innymi rejestrację danych studenta, edycję dziennika, przesyłanie do weryfikacji, dodawanie uwag, zmianę statusów, wystawienie oceny końcowej, generowanie PDF i archiwizację.

- **F1–F3** – tworzenie dokumentacji przez studenta i praca na dzienniku praktyk.
- **F4** – praca z efektami uczenia się podczas weryfikacji dokumentu.
- **F5–F8** – przesyłanie do weryfikacji, blokada edycji, uwagi opiekuna i zmiana statusów.
- **F9–F10** – wystawienie oceny końcowej i wygenerowanie raportu PDF.
- **F12** – archiwizacja zatwierdzonej dokumentacji.

## Podsumowanie projektu

Repozytorium prezentuje model logiki biznesowej systemu obsługi praktyk zawodowych za pomocą diagramów Mermaid osadzonych bezpośrednio w README. Takie rozwiązanie pozwala zachować czytelność dokumentacji, łatwość edycji oraz dobrą widoczność projektu na GitHubie bez potrzeby używania plików PNG lub zrzutów ekranu. [file:1][web:53][web:54]
