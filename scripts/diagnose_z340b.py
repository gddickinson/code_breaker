"""Find the break in Z340 section B using the published solution as ground truth."""
from collections import Counter, defaultdict

from codebreaker.mysteries.zodiac import load
from codebreaker.text import letters

z, t = load("z340.txt"), letters(load("z340_solved.txt"))
R, C, S = 9, 17, 153
sec, tr = z[S:2 * S], t[S:2 * S]
pos = lambda i, a=0, b=0: ((i + a) % R) * C + (2 * i + b) % C
key = defaultdict(Counter)
for i in range(S):
    key[z[:S][pos(i)]][t[i]] += 1
for s, p in zip(z[2 * S:], t[2 * S:]):
    key[s][p] += 1
for i in range(99):
    key[sec[pos(i)]][tr[i]] += 1
major = {s: c.most_common(1)[0][0] for s, c in key.items()}
ok = lambda i, a, b: major.get(sec[pos(i, a, b)]) == tr[i]
print("agreement by reading position", "".join("#" if ok(i, 0, 0) else "." for i in range(S)))
res = sorted(((sum(ok(i, a, b) for i in range(cut, S)) / (S - cut), cut, a, b) for cut in range(85, 125) for a in range(R) for b in range(C)), reverse=True)[:6]
print("single cut, new phase", [(round(v, 2), c, a, b) for v, c, a, b in res])
used = [sec[pos(i)] for i in range(99)]
print("as-written rows 6-9"); [print(sec[r * C:(r + 1) * C]) for r in range(5, R)]
print("target plain rows"); [print(tr[r * C:(r + 1) * C]) for r in range(5, R)]

left = sorted(set(range(S)) - {pos(i) for i in range(99)})
inleft = set(left)
hits = []
for start in left:
    for dr in range(R):
        for dc in range(C):
            r0, c0 = start // C, start % C
            seq = [((r0 + j * dr) % R) * C + (c0 + j * dc) % C for j in range(S - 99)]
            if len(set(seq)) == len(seq) and set(seq) == inleft:
                hits.append((sum(major.get(sec[p]) == tr[99 + j] for j, p in enumerate(seq)) / (S - 99), start, dr, dc))
print("regular walks over unused cells", len(hits), sorted(hits, reverse=True)[:5])
best = [i for i in range(99, S) if ok(i, 0, 0)]
print("where the 54 remaining letters could sit: cells with matching key letter", sum(any(major.get(sec[p]) == tr[i] for p in left) for i in range(99, S)))
for cut_row in range(S):
    pass
for name, seq in (("swap rows", None),):
    rowsc = [sec[r * C:(r + 1) * C] for r in range(R)]
    import itertools
    results = []
    for a, b in itertools.combinations(range(R), 2):
        rr = list(rowsc); rr[a], rr[b] = rr[b], rr[a]
        s2 = "".join(rr)
        results.append((sum(major.get(s2[pos(i)]) == tr[i] for i in range(S)) / S, a, b))
    print("row swap agreement (baseline", sum(ok(i, 0, 0) for i in range(S)) / S, ")", sorted(results, reverse=True)[:4])
