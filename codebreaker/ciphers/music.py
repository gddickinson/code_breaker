"""Music ciphers (Round 81): letters as notes. Rules from the recorded Wikipedia page 'Musical cryptogram'
(data/sources/scripts/wp_musical_cryptogram.txt).

German method: letters that are German note names become those notes (B = B-flat, H = B-natural, S = Es = E-flat,
A, C-G as written); other letters are left out, as composers did (Schumann's ASCH, Bach's BACH, Shostakovich's DSCH).
French method: H-N, O-U and V-Z are written under A-G, so every letter has a note: A, O, V -> A; B, I, P, W -> B;
and so on, with H kept as the German B-natural, as the recorded Haydn motif shows (HAYDN = B, A, D, D, G). Many letters share a note, so reading it back means choosing among them: the attack is a beam search with
the quadgram language model, bar lines kept as word breaks.
Note substitution: a keyword-mixed alphabet onto 26 chromatic pitches (C4 upward); a simple substitution in notes."""
import numpy as np

from ..attacks import classical as X
from ..languages import model
from ..text import A, keyed_alphabet, letters
from .base import Param, add
from .monoalphabetic import word_gen

FAM = "Music"
GERMAN = {"A": "A", "B": "B♭", "C": "C", "D": "D", "E": "E", "F": "F", "G": "G", "H": "B♮", "S": "E♭"}
GERMAN_BACK = {v: k for k, v in GERMAN.items()}
NOTES7 = ["A", "B♮", "C", "D", "E", "F", "G"]
FRENCH = {**{c: NOTES7[i % 7] for i, c in enumerate(A)}, "H": "B♮"}  # rows under A..G; H keeps the German B-natural, as in HAYDN
FRENCH_SETS = {n: [c for c in A if FRENCH[c] == n] for n in NOTES7}
CHROMATIC = [f"{n}{o}" for o in (4, 5, 6) for n in ("C", "C♯", "D", "D♯", "E", "F", "F♯", "G", "G♯", "A", "A♯", "B")][:26]


def german_e(t):
    return " ".join(GERMAN[c] for c in letters(t) if c in GERMAN)


def german_d(t):
    return "".join(GERMAN_BACK.get(n, "") for n in t.split())


def french_e(t):
    return " | ".join(" ".join(FRENCH[c] for c in letters(w)) for w in t.split() if letters(w))


def french_d(t, lang="en"):
    """A many-to-one code has no exact decryption, only a most likely reading: the beam search below. Re-encrypting
    the reading gives the same notes; how close it is to the original message is measured in tests/test_music.py."""
    return french_a(t, lang)["spaced"]


def _beam(notes: list[str], table: np.ndarray, width: int = 300) -> str:
    beams = [(0.0, "")]
    for n in notes:
        if n == "|":
            beams = [(s, t + " ") for s, t in beams]
            continue
        nxt = []
        for s, t in beams:
            core = t.replace(" ", "")
            for c in FRENCH_SETS[n]:
                q = core[-3:] + c
                inc = table[((ord(q[0]) - 65) * 17576 + (ord(q[1]) - 65) * 676 + (ord(q[2]) - 65) * 26 + ord(q[3]) - 65)] if len(q) == 4 else 0.0
                nxt.append((s + inc, t + c))
        nxt.sort(key=lambda x: -x[0])
        beams = nxt[:width]
    return beams[0][1].strip()


def french_a(ct, lang="en"):
    """Choose each note's letter by a beam search over quadgrams (no key exists, only the shared-note ambiguity)."""
    notes = [x for x in ct.replace("|", " | ").split() if x == "|" or x in FRENCH_SETS]
    plain = _beam(notes, model(lang)["table"])
    return X.result(plain, {}, "beam search over each note's letters with quadgrams", lang) | {"spaced": plain}


def notesub_e(t, keyword=""):
    k = keyed_alphabet(letters(keyword))
    return " ".join(CHROMATIC[k.index(c)] for c in letters(t))


def notesub_d(t, keyword=""):
    k = keyed_alphabet(letters(keyword))
    return "".join(k[CHROMATIC.index(n)] for n in t.split() if n in CHROMATIC)


def notesub_a(ct, lang="en"):
    return X.solve_symbols([n for n in ct.split() if n in CHROMATIC], lang)


add(id="music_german", name="Musical cryptogram (German)", family=FAM, era="Renaissance onward; Bach, Schumann, Shostakovich",
    summary="Spell a name in note names: B is B-flat, H is B-natural, S is E-flat. Letters with no note are left out.",
    how="German note names run A to H, with B for B-flat and H for B-natural, and 'Es' (S) for E-flat. Bach spelled his name B-A-C-H, Shostakovich D-S-C-H as D, E-flat, C, B-natural, Schumann A-S-C-H.",
    weakness="It hides nothing: anyone who knows the note names reads it. Its use is homage, a signature written into the music.",
    encrypt=german_e, decrypt=german_d, key={}, example="Bach", attack=lambda ct, lang="en": X.result(german_d(ct), {}, "read the note names", lang),
    attack_name="Read the note names", keygen=lambda r: {})

add(id="music_french", name="Musical cryptogram (French)", family=FAM, era="Late 19th century; Ravel's Menuet sur le nom d'Haydn (1909)",
    summary="Every letter gets a note: the alphabet is written in rows of seven under A to G.",
    how="Write A-G, then H-N, O-U and V-Z in rows under the notes A to G. Each letter becomes the note above its column, so A, O and V are all 'A'. H keeps its German meaning, B-natural: Ravel's HAYDN for the 1909 Haydn centenary is B, A, D, D, G.",
    weakness="Three or four letters share each note, so the music hides little: a reader tries each note's letters and keeps the ones that make words, which a language model does quickly.",
    encrypt=french_e, decrypt=french_d, key={}, example="Meet me at the old bridge", attack=french_a,
    attack_name="Beam search over each note's letters", keygen=lambda r: {})

add(id="music_notes", name="Note substitution", family=FAM, era="Puzzle tradition; secret melodies in letters and novels",
    summary="A keyword-mixed alphabet written as 26 pitches: a real cipher, but a simple substitution.",
    how="Mix the alphabet with a keyword, then write its n-th letter as the n-th chromatic pitch from middle C (C4, C#4, D4 ...). The tune sounds random but each pitch is always the same letter.",
    weakness="Pitches are just symbols: count them and solve as a simple substitution, as with runes or pigpen.",
    encrypt=notesub_e, decrypt=notesub_d, key={"keyword": "ENIGMA"}, example="Meet me at the old bridge at dawn",
    params=[Param("keyword", "Keyword")], attack=notesub_a, attack_name="Relabel the pitches and anneal", keygen=word_gen)
