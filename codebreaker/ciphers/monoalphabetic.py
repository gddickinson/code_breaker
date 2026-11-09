"""Ciphers that replace each letter with one fixed symbol."""
from ..attacks import classical as X
from ..languages import keywords
from ..text import A, keyed_alphabet, letters, to_ints, to_text
from .base import Param, add

P_SHIFT = Param("shift", "Shift (0-25)", "int")
P_WORD = Param("keyword", "Keyword")
FAM = "Monoalphabetic"


def word_gen(r):
    return {"keyword": r.choice(keywords("en", 2500, 5))}


def caesar_e(t, shift=3):
    return to_text((to_ints(t) + int(shift)) % 26)


def caesar_d(t, shift=3):
    return caesar_e(t, -int(shift))


def caesar_a(ct, lang="en"):
    return X.keyspace(lambda shift: caesar_d(ct, shift), ({"shift": s} for s in range(26)), lang, "tried all 26 shifts")


add(id="caesar", name="Caesar shift", family=FAM, era="Ancient Rome, c. 50 BC",
    summary="Shift every letter a fixed distance along the alphabet.",
    how="Number the letters A=0 to Z=25. Encrypt with (letter + shift) mod 26 and decrypt with (letter - shift) mod 26. Suetonius records Julius Caesar using a shift of three.",
    weakness="There are only 26 keys, so a computer or a patient person simply tries them all.",
    encrypt=caesar_e, decrypt=caesar_d, key={"shift": 3}, example="Attack at dawn", params=[P_SHIFT],
    attack=caesar_a, attack_name="Try all 26 shifts and score each as language", keygen=lambda r: {"shift": r.randint(1, 25)})


def rot13(t):
    return caesar_e(t, 13)


add(id="rot13", name="ROT13", family=FAM, era="Usenet, 1980s", summary="A Caesar shift of 13, which is its own inverse.",
    how="Because 13 + 13 = 26, the same operation both encrypts and decrypts. It was used online to hide spoilers.",
    weakness="There is no key at all. It only stops accidental reading.", encrypt=rot13, decrypt=rot13, key={}, example="Spoiler alert",
    attack=lambda ct, lang="en": X.result(rot13(ct), {}, "apply ROT13 again", lang), attack_name="Apply it again", keygen=lambda r: {})


def atbash(t):
    return to_text(25 - to_ints(t))


add(id="atbash", name="Atbash", family=FAM, era="Hebrew scribes, c. 600 BC", summary="Mirror the alphabet: A becomes Z, B becomes Y.",
    how="Originally a Hebrew substitution. It appears in the Book of Jeremiah, where Sheshach stands for Babel. Each letter is replaced by the letter the same distance from the other end.",
    weakness="It has no key. Once you know the system, the message is open.", encrypt=atbash, decrypt=atbash, key={}, example="Babylon has fallen",
    attack=lambda ct, lang="en": X.result(atbash(ct), {}, "apply Atbash again", lang), attack_name="Apply it again", keygen=lambda r: {})


def _inv(a):
    return pow(int(a), -1, 26)


def affine_e(t, a=5, b=8):
    return to_text((int(a) * to_ints(t) + int(b)) % 26)


def affine_d(t, a=5, b=8):
    return to_text((_inv(a) * (to_ints(t) - int(b))) % 26)


UNITS = [1, 3, 5, 7, 9, 11, 15, 17, 19, 21, 23, 25]


def affine_a(ct, lang="en"):
    return X.keyspace(lambda a, b: affine_d(ct, a, b), ({"a": a, "b": b} for a in UNITS for b in range(26)), lang, "tried all 312 keys")


add(id="affine", name="Affine", family=FAM, era="Mathematical generalisation of Caesar", summary="Multiply and shift: E(x) = ax + b mod 26.",
    how="The multiplier a must share no factor with 26, otherwise two letters collide and decryption fails. Decrypt using the modular inverse of a.",
    weakness="Only 312 keys exist, and two known letters solve a pair of linear equations.", encrypt=affine_e, decrypt=affine_d, key={"a": 5, "b": 8},
    example="Affine ciphers are linear", params=[Param("a", "Multiplier a (coprime to 26)", "int"), Param("b", "Shift b", "int")],
    attack=affine_a, attack_name="Try all 312 keys", keygen=lambda r: {"a": r.choice(UNITS), "b": r.randint(0, 25)})


def sub_e(t, keyword="ZEBRA"):
    table = str.maketrans(A, keyed_alphabet(keyword))
    return letters(t).translate(table)


def sub_d(t, keyword="ZEBRA"):
    table = str.maketrans(keyed_alphabet(keyword), A)
    return letters(t).translate(table)


add(id="substitution", name="Simple substitution", family=FAM, era="Antiquity; broken by al-Kindi, 9th century",
    summary="Any rearrangement of the alphabet: about 4x10^26 keys.",
    how="Each plaintext letter maps to one fixed ciphertext letter. Enter a keyword to build the mixed alphabet, or think of it as an arbitrary permutation.",
    weakness="A huge keyspace does not help, because letter and pattern frequencies survive. Al-Kindi described frequency analysis over 1,100 years ago. Modern solvers anneal over keys and score quadgrams.",
    encrypt=sub_e, decrypt=sub_d, key={"keyword": "ZEBRA"}, example="Frequency analysis defeats this", params=[P_WORD],
    attack=X.substitution, attack_name="Simulated annealing over the 26! alphabet orders, scored by quadgrams", keygen=word_gen)


BACON = {c: format(i, "05b").replace("0", "A").replace("1", "B") for i, c in enumerate(A)}
UNBACON = {v: k for k, v in BACON.items()}


def bacon_e(t):
    return " ".join(BACON[c] for c in letters(t))


def bacon_d(t):
    s = [c for c in t.upper() if c in "AB"]
    return "".join(UNBACON["".join(s[i:i + 5])] for i in range(0, len(s) - 4, 5))


add(id="baconian", name="Baconian", family=FAM, era="Francis Bacon, 1605", summary="Five-bit letters written with two symbols, an early binary code.",
    how="Each letter becomes five A/B symbols. Bacon hid them steganographically by using two typefaces in an innocent cover text.",
    weakness="Once the two classes are spotted the code is fixed and open.", encrypt=bacon_e, decrypt=bacon_d, key={}, example="Hidden in plain sight",
    attack=lambda ct, lang="en": X.result(bacon_d(ct), {}, "read 5-bit groups", lang), attack_name="Read the fixed code", keygen=lambda r: {})

MORSE = dict(zip(A, ".- -... -.-. -.. . ..-. --. .... .. .--- -.- .-.. -- -. --- .--. --.- .-. ... - ..- ...- .-- -..- -.-- --..".split()))
UNMORSE = {v: k for k, v in MORSE.items()}


def morse_e(t):
    return " ".join(MORSE[c] for c in letters(t))


def morse_d(t):
    return "".join(UNMORSE.get(g, "") for g in t.replace("/", " ").split())


add(id="morse", name="Morse code", family="Codes", era="Vail and Morse, 1840s", summary="Variable-length dots and dashes for telegraphy.",
    how="Common letters get short codes: E is one dot. It is an encoding rather than a cipher, since no secret is involved.",
    weakness="It provides no secrecy, though the variable lengths foreshadow Huffman compression.", encrypt=morse_e, decrypt=morse_d, key={}, example="Save our souls",
    attack=lambda ct, lang="en": X.result(morse_d(ct), {}, "read the public code", lang), attack_name="Read the public code", keygen=lambda r: {})


def square(keyword="", merge=("J", "I")):
    return keyed_alphabet(letters(keyword).replace(*merge), A.replace(merge[0], ""))


def poly_e(t, keyword=""):
    s = square(keyword)
    return " ".join(f"{s.index(c) // 5 + 1}{s.index(c) % 5 + 1}" for c in letters(t).replace("J", "I"))


def poly_d(t, keyword=""):
    s, d = square(keyword), "".join(c for c in t if c.isdigit())
    return "".join(s[(int(d[i]) - 1) * 5 + int(d[i + 1]) - 1] for i in range(0, len(d) - 1, 2))


def digit_pairs_attack(ct, lang="en"):
    return X.solve_symbols(X.pairs("".join(c for c in ct if c.isdigit())), lang)


add(id="polybius", name="Polybius square", family=FAM, era="Greek historian Polybius, c. 150 BC", summary="Each letter becomes its row and column in a 5x5 grid.",
    how="Polybius proposed it for signalling with torches. I and J share a cell. It turns letters into digit pairs, and that fractionation idea drives many later ciphers.",
    weakness="The digit pairs are still a simple substitution, so frequency analysis applies.", encrypt=poly_e, decrypt=poly_d, key={"keyword": ""}, example="Torches on the hill", params=[P_WORD],
    attack=digit_pairs_attack, attack_name="Treat digit pairs as symbols and anneal", keygen=word_gen)


TAP = square("", ("K", "C"))


def tap_e(t):
    return " ".join("." * (TAP.index(c) // 5 + 1) + " " + "." * (TAP.index(c) % 5 + 1) for c in letters(t).replace("K", "C"))


def tap_d(t):
    g = t.split()
    return "".join(TAP[(len(g[i]) - 1) * 5 + len(g[i + 1]) - 1] for i in range(0, len(g) - 1, 2))


add(id="tap", name="Tap code", family="Codes", era="Prisoners of war, 20th century", summary="A Polybius square tapped on a wall.",
    how="Tap the row number, pause, then tap the column number. C and K share a cell. American prisoners in Vietnam used it famously.",
    weakness="It is a public code that offers concealment only.", encrypt=tap_e, decrypt=tap_d, key={}, example="Stay strong",
    attack=lambda ct, lang="en": X.result(tap_d(ct), {}, "read the public code", lang), attack_name="Read the public code", keygen=lambda r: {})


def a1z26_e(t):
    return " ".join(str(int(i) + 1) for i in to_ints(t))


def a1z26_d(t):
    return "".join(A[int(x) - 1] for x in t.split())


add(id="a1z26", name="A1Z26", family="Codes", era="Traditional", summary="Letters become their alphabet positions.",
    how="A=1 through Z=26. It is often a first step inside puzzle chains.", weakness="It has no key.", encrypt=a1z26_e, decrypt=a1z26_d, key={}, example="Number stations",
    attack=lambda ct, lang="en": X.result(a1z26_d(ct), {}, "read the public code", lang), attack_name="Read the public code", keygen=lambda r: {})
