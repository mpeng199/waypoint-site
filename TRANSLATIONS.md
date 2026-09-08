# The ten translations

Waypoint's front page exists in the ten languages Local Law 30 names. They are
not notices about an English page. They are the page.

This file is for the person who reviews one of them. It says where the words
live, which decisions were made on purpose, what the linter will refuse, and
what is still an open question for somebody who actually speaks the language.

---

## Where the words are

| What | File | Key |
|---|---|---|
| The page's own chrome — masthead, emergency panel, promise, footer | `i18n.py` | `UI[language]` |
| The line under each of the seventeen headings | `i18n.py` | `BLURBS[language]` |
| The short chip labels in the jump row | `i18n.py` | `SHORT[language]` |
| The seventeen headings themselves | `build_help.py` | `LANGUAGES[…]["needs"]` |
| Month names and how a date span reads | `i18n.py` | `MONTHS`, `DATE_SPAN` |

Nothing else on a language page is translated, and that is deliberate. A
resource's name is a proper noun and its phone number is a number: both are
what somebody has to say and dial. Their English descriptions are left in
English rather than machine-guessed, and `UI[language]["english"]` is the one
sentence that says so and says how to get an interpreter.

To read one language end to end, in the order a reader meets it:

```bash
python3 review_translations.py spanish
```

That prints every string in that language beside its English source, grouped
the way the page is, and is the file to hand a native speaker.

---

## Read this before you change a string

### One addressee per language

Spanish addresses the reader as **usted** from the masthead to the footer.
Polish is **impersonal** (`potrzebujesz`, not `Pan/Pani`). Chinese uses **您**.
Urdu uses **آپ**. Russian and French use **вы / vous**. A page that slides
between registers reads as though two people wrote it, which on a page
somebody opens frightened is a reason not to trust it.
`check_language_voice` fails when one language uses both.

Spanish uses **leísmo de cortesía** throughout — `le atienden`, `le lleva` —
which is what the RAE sanctions for `usted` and what Latin American Spanish
does. It is consistent on every surface. Do not "fix" it to `lo/la` in one
place and leave the rest.

### Nothing may agree with the reader's gender

The seventeen headings are the reader speaking — "I need food" — and in
Polish, Russian, Spanish, Arabic, Urdu, French and Bengali the obvious way to
write that agrees with a gender the site cannot know. `Nie jestem bezpieczny`,
`Я служил`, `estoy solo`, `خدمت`, `اکیلا`, `je suis seule`, `তরুণ`: every one
of those told half the readers the page was not written for them.

The fix is always a construction that does not agree — a noun instead of a
past tense, an adverb instead of an adjective. `Mam za sobą służbę wojskową`.
`أنا شخص صغير السن`. `আমি কমবয়সী আর একা`. `check_language_voice` fails on the
endings rather than on a word list, so a new gendered ending is caught even if
the word is new.

### Short sentences

The English pages hold a grade-9 reading level. That cannot be measured in ten
scripts, so what is measured instead is what it is a proxy for: the English
site runs a median of about eleven words a sentence, and all ten translations
land between nine and twelve. `check_language_sentence_length` fails a median
over sixteen or any sentence over thirty-four words. A page quietly rewritten
in the register of a government leaflet fails here.

### Punctuation belongs to the script

Arabic and Urdu set the comma **،** the semicolon **؛** and the question mark
**؟**. Urdu ends a sentence on **۔** and Bengali on **।**. Chinese sets
**，。？！** full-width. The Latin marks are mirrored the wrong way against
right-to-left text and leave a hole between two han characters.
`check_translated_punctuation_is_the_readers` fails on any of them.

French puts a space before `? ! ; :` and it is **not an ordinary space** — an
ordinary one lets the mark wrap to a line of its own. Use U+202F (narrow
no-break) before `? ! ;` and U+00A0 (no-break) before `:`. Six plain ones had
shipped. `check_french_sets_the_space_before_its_punctuation` fails them.

### Proper nouns are not translated

SNAP, Medicaid, MetroCard, Access-A-Ride, Homebase and **Fair Fares NYC** are
what you have to say on the phone and type into a search box. "MetroCard a
mitad de precio" describes Fair Fares NYC accurately and names it not at all,
and a reader who cannot read English cannot guess the English name the way an
English speaker can. The Korean page had `메트로카드`, which is how the word
sounds and not what is printed on the card.
`check_program_names_survive_translation` fails a blurb that only describes.

### "Student" is not one word in every language

English "student" covers a nine-year-old and a doctoral candidate. Polish,
French, Russian and Haitian Creole make you choose, and all four had chosen
the university word: `uczeń` is six to eighteen and at school where `student`
starts at nineteen; a sixteen-year-old at a lycée is an **élève**, never an
*étudiant*; Russian splits **школьник** from *студент*; Kreyòl follows French
with **elèv** against *etidyan*.

Waypoint's own copy settles it. students.html says most volunteers are
fourteen to eighteen, and the sign-up form asks for "School & grade" and
suggests *"e.g. Stuyvesant, 11th"* — a New York City public high school, and
the eleventh grade. Four pages were saying, in the only word those languages
have for it, that this is a corps of undergraduates.

Spanish `Estudiantes`, Chinese 学生, Korean 학생, Bengali শিক্ষার্থী, Arabic
الطلاب and Urdu طلبہ genuinely cover both and are untouched.
`check_the_student_word_is_the_school_one` fails a return to the university
word. **If the corps ever does take college students, that guard is where to
say so, and the fix is one word per language.**

### One word per thing

The Chinese page called disability `残疾` in the heading and `残障` in the chip
beside it. Nobody notices this in a language they do not speak and nobody
misses it in one they do. `check_one_word_per_thing_in_each_language` holds a
short list of synonym sets and fails when two members of one set appear.

The written exception is French: the city is **New York** and a person from it
is a **New-Yorkais**, so the hyphen is right in exactly one of the two.

---

## The glossary

Checked against **ACCESS NYC**, which publishes the same programs in the same
ten languages: `access.nyc.gov/{es,ru,ko,ht,zh-hant,fr,pl,bn,ar,ur}`. A reader
holding a letter from HRA should see the same noun here that is on the letter.

| Concept | The word we use | Source |
|---|---|---|
| Cash Assistance (es) | asistencia en efectivo | ACCESS NYC |
| Cash Assistance (ru) | Денежное пособие | ACCESS NYC |
| Cash Assistance (ht) | Èd an lajan kach | ACCESS NYC (*Asistans Lajan Kach*) |
| Cash Assistance (ur) | نقد امداد | ACCESS NYC |
| Cash Assistance (ar) | مساعدة نقدية | ACCESS NYC |
| Cash Assistance (bn) | নগদ সহায়তা | ACCESS NYC |
| Cash Assistance (ko) | 현금 지원 | ACCESS NYC |
| shelter (es) | refugio | ACCESS NYC |
| shelter (ar) | مأوى | ACCESS NYC |
| shelter (ur) | پناہ گاہ | ACCESS NYC |
| shelter (bn) | আশ্রয় | ACCESS NYC |
| benefits (ur) | مراعات | ACCESS NYC |
| benefits (ar) | المزايا | ACCESS NYC |
| benefits (ht) | avantaj | ACCESS NYC |
| benefits (pl) | świadczenia | ACCESS NYC |
| benefits (fr) | prestations | ACCESS NYC |
| benefits (es) | beneficios | ACCESS NYC |
| childcare (es) | cuidado infantil | ACCESS NYC |
| half-price MetroCard | Fair Fares NYC | nyc.gov/site/fairfares |
| senior centre | *older adult* wording throughout | NYC Aging renamed these Older Adult Centers |

**Two places we deliberately do not follow the city.** ACCESS NYC's Korean
says `대피소` for shelter, which is an evacuation shelter — Korean community
organisations say `쉼터`, and so do we. Its Russian says `приют`, which is also
an orphanage and an animal shelter; we say `ночлег`. Where the city's own
translation is worse, we do not follow it, but we write down that we didn't.

---

## The crisis line

The English reads *"feeling unsafe with yourself"*, which is a euphemism
English crisis services really do use. Word for word it is a euphemism
nowhere else, and all ten had it word for word:

- `No se siente seguro consigo mismo` — low self-confidence
- `您担心自己的安全` — worry about being physically attacked, which is the 911
  card one row up
- `নিজেকে নিয়ে নিরাপদ বোধ করছেন না` — close to nothing at all

Every one of the ten now names the thought. The Spanish is the phrase the 988
Lifeline uses in its own Spanish materials — *pensamientos de hacerte daño* —
in this site's `usted` register. `check_the_crisis_line_is_not_a_calque`
requires each language's crisis label **and** crisis blurb to name harming
oneself in that language's own words, and fails if the calque returns.

**How to be answered in your own language** is now on every page, in
`sos_note`. 988 connects a Spanish speaker directly on option 2, and puts an
interpreter on 240-odd other languages if the caller says the language's name
in English; 311, 911 and the domestic-violence line carry interpretation too.
None of it was anywhere on the ten pages, so the page that exists *because*
somebody cannot read English handed them a number that answers in English.

That note must not print a diallable number as text — the numbers above it are
tap targets, and `check_language_numbers_dial` fails a page that repeats one in
prose. Say "the crisis line", not the digits.

---

## Running the checks

```bash
python3 build_help.py && python3 check.py
```

`check.py` holds fifteen guards over the translations: five that predate this
review (`check_language_voice`, `check_language_sentence_length`,
`check_language_header`, `check_language_numbers_dial`,
`check_language_round_trip`) and ten added by it.

One of those ten guards nothing about the words. `check.py` and
`build_help.py` both refuse Python's bytecode cache before they import
anything, because CPython validates a `.pyc` against the source's mtime **in
whole seconds** and its size — so an edit that lands in the same second and
changes no bytes is invisible to `import`. 残疾 and 残障 are six bytes each.
mutate.py flips exactly that pair, and the whole suite reported *3800 passed,
0 failed*, while the guard written to catch it fires the instant the cache is
gone. A rebuild loop is the fastest loop this repo has, so this was reachable
in ordinary work, and it silently weakened every guard that reads i18n.py.
`check_the_guards_read_the_file_not_a_cache` is the guard on the refusal.

### If you add a guard: match stems, not words

Two of the ten guards here read correctly and matched nothing, and mutate.py
is the only reason anybody knows.

The student guard tested for the substring `"student"`. Polish declines: the
nominative plural is **studenci**, the stem's t goes to c, and `"studenci"`
does not contain `"student"`. The guard ran, asserted, passed, and was blind.
Russian would have gone the same way — студент, студентам, студенческий.

The same trap is waiting in any guard that names a Polish or Russian noun in
one case: `tłumacza` is the genitive of `tłumacz`, `переводчика` of
`переводчик`, `krzywdy` of `krzywda`. Match `tłumacz`, not `tłumacza`. A guard
matching the inflected form is a false alarm the moment somebody rewrites the
sentence into a different case, and blind in the other direction.

Every mutation that touches i18n.py is caught: **10 of 10**. If you add a
guard, add its mutation in the same commit, and watch it fail before you watch
it pass.

```bash
python3 mutate.py          # breaks the site on purpose, one way at a time,
                           # and reports anything check.py fails to notice
python3 audit_guards.py    # names any guard that has stopped observing
```

`mutate.py` edits real files in place and restores them afterwards. Run it in
the foreground and let it finish. If it dies half way: `git checkout -- .`
then `python3 build_help.py`.

---

## Still open, for somebody who speaks the language

Nothing here is machine output, and one careful non-native review pass has
been over all ten (September 2026) for calques, register, grammar, typography
and terminology. That pass does not replace a native reader — it removes the
errors a careful non-native reader can see. These are the questions it could
not settle:

- **The Chinese page is Simplified only (`zh-Hans`).** Local Law 30 names the
  language as "Chinese (Simplified, Traditional)" — both — and NYC's own
  agencies publish Traditional: ACCESS NYC serves `zh-hant`, for the older
  Cantonese-speaking population, while Simplified serves more recent arrivals
  from the mainland. Half the designated readership currently gets the script
  it does not read most comfortably. Serving both is a build decision, not a
  translation one, so it is left here rather than done.
- **Whether the corps takes college students.** See "student" below. If it
  does, four words revert.
- **Korean `제대 군인`** for veterans. The US Department of Veterans Affairs is
  `재향군인부` in Korean, so `재향군인` may be the word a Korean-speaking veteran
  in New York expects.
- **Haitian `Depo manje`** for a food pantry is literally a food warehouse. It
  is used that way in the New York Haitian community, which is why it stayed.
- **Bengali writes the city `নিউ ইয়র্ক`** (two words); ACCESS NYC writes
  `নিউইয়র্ক` (one). Both are in use. Ours is consistent with itself, which the
  linter enforces.
