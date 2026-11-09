"""Use the published Z340 solution as ground truth to test each section's assumed reading order."""
from collections import Counter, defaultdict

from codebreaker.mysteries.zodiac import load
from codebreaker.text import letters


def consistency(sym, plain):
    """Share of positions agreeing with the majority letter of their symbol: high if aligned."""
    m = defaultdict(Counter)
    for s, p in zip(sym, plain):
        m[s][p] += 1
    return sum(c.most_common(1)[0][1] for c in m.values()) / len(sym)


z, t = load("z340.txt"), letters(load("z340_solved.txt"))
print(len(z), len(t), t[:60])
R, C = 9, 17
size = R * C
def knight(sec, dr=1, dc=2):
    return "".join(sec[(i * dr % R) * C + (i * dc) % C] for i in range(size))
def rev_map(sec, dr=1, dc=2):
    out = [""] * size
    for i, ch in enumerate(sec):
        out[(i * dr % R) * C + (i * dc) % C] = ch
    return "".join(out)
for name, a, b in (("A", 0, size), ("B", size, 2 * size)):
    sec, tr = z[a:b], t[a:b]
    print(name, "as written", round(consistency(sec, tr), 3))
    for dc in range(1, 17):
        for f, fn in (("forward", knight), ("inverse", rev_map)):
            v = consistency(fn(sec, 1, dc), tr)
            if v > 0.55:
                print(" ", name, f, "dc", dc, round(v, 3))
print("C last rows", round(consistency(z[2 * size:], t[2 * size:]), 3))

# Section B: which single-row changes restore consistency?
sec, tr = z[size:2 * size], t[size:2 * size]
base = knight(sec)
rows = [base[r * C:(r + 1) * C] for r in range(R)]
trr = [tr[r * C:(r + 1) * C] for r in range(R)]
print("row consistency", [round(consistency("".join(rows[:r] + rows[r + 1:]), "".join(trr[:r] + trr[r + 1:])), 3) for r in range(R)])
best = []
for a in range(R):
    for b in range(C):
        s = "".join(sec[((i + a) % R) * C + (2 * i + b) % C] for i in range(size))
        best.append((round(consistency(s, tr), 3), a, b))
print("best start offsets", sorted(best, reverse=True)[:5])
# Mismatch map: positions disagreeing with the symbol key learned from section A and C
from collections import Counter as Cn, defaultdict as dd
key = dd(Cn)
for s, p in zip(knight(z[:size]) + z[2 * size:], t[:size] + t[2 * size:]):
    key[s][p] += 1
good = [key[s].most_common(1)[0][0] == p if s in key else None for s, p in zip(base, tr)]
for r in range(R):
    print("".join("?" if g is None else "#" if g else "." for g in good[r * C:(r + 1) * C]), base[r * C:(r + 1) * C], trr[r])
