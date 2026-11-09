"""Public-key cryptography at teaching sizes, with the attacks that defeat weak parameters."""
import hashlib

from ..attacks import modern as M
from .base import Param, add
from .modern_symmetric import xor_bytes

FAM = "Public key"
P, Q = 1000000007, 998244353


def _ints(t):
    return [int(x) for x in t.split()]


def rsa_e(t, n=P * Q, e=65537, d=None):
    return " ".join(str(pow(b, int(e), int(n))) for b in t.encode())


def rsa_d(t, n=P * Q, d=None, e=65537):
    n = int(n)
    if not d:
        raise ValueError("private exponent d required")
    return bytes(pow(c, int(d), n) for c in _ints(t)).decode(errors="replace")


D_EX = pow(65537, -1, (P - 1) * (Q - 1))
add(id="rsa", name="RSA", family=FAM, era="Rivest, Shamir, Adleman 1977; Cocks at GCHQ 1973", summary="Security from the difficulty of factoring.",
    how="Pick primes p and q, publish n = pq and e, and keep d = e^-1 mod (p-1)(q-1). Encrypt with m^e mod n. This demo encrypts per byte with a 60-bit modulus to teach the arithmetic. That is deliberately insecure.",
    weakness="Per-byte textbook RSA is a substitution cipher. Weak parameters fall to factoring, Wiener's small-d attack, Hastad's broadcast attack or common-modulus attacks. All four are demonstrated.",
    encrypt=rsa_e, decrypt=rsa_d, key={"n": P * Q, "e": 65537, "d": D_EX}, example="RSA", params=[Param("n", "Modulus n", "text"), Param("e", "Public exponent e", "text"), Param("d", "Private exponent d", "text")], demo_attack=M.rsa_suite, modern=True)

PRIME, G = 2147483647, 7


def _dh_key(a, b, p, g):
    return hashlib.sha256(str(pow(pow(int(g), int(a), int(p)), int(b), int(p))).encode()).digest()


def dh_e(t, a=123456, b=654321, p=PRIME, g=G):
    return xor_bytes(t.encode(), _dh_key(a, b, p, g)).hex()


def dh_d(t, a=123456, b=654321, p=PRIME, g=G):
    return xor_bytes(bytes.fromhex(t), _dh_key(a, b, p, g)).decode(errors="replace")


P_DH = [Param("a", "Alice's secret", "int"), Param("b", "Bob's secret", "int"), Param("p", "Prime p", "text"), Param("g", "Generator g", "text")]
add(id="dh", name="Diffie-Hellman", family=FAM, era="Diffie and Hellman, 1976", summary="Agree on a secret over a public channel.",
    how="Alice sends g^a and Bob sends g^b. Each can compute g^ab, but an eavesdropper would have to solve a discrete logarithm. The derived secret then encrypts the message.",
    weakness="A small group falls to baby-step giant-step, and a smooth p-1 to Pohlig-Hellman. Without authentication, a man in the middle simply impersonates both sides.",
    encrypt=dh_e, decrypt=dh_d, key={"a": 123456, "b": 654321, "p": PRIME, "g": G}, example="Meet me in the group", params=P_DH, demo_attack=M.dlog_bsgs, modern=True)


def eg_e(t, p=PRIME, g=G, h=None, k=99991):
    p, g, h, k = int(p), int(g), int(h), int(k)
    return f"{pow(g, k, p)} " + " ".join(str(b * pow(h, k, p) % p) for b in t.encode())


def eg_d(t, p=PRIME, x=424242):
    p = int(p)
    c1, *rest = _ints(t)
    s = pow(pow(c1, int(x), p), -1, p)
    return bytes(c * s % p for c in rest).decode(errors="replace")


H_EX = pow(G, 424242, PRIME)
add(id="elgamal", name="ElGamal", family=FAM, era="Taher ElGamal, 1985", summary="Public-key encryption built on discrete logs.",
    how="Choose a fresh random k per message. Send g^k and m*h^k. The key dialog holds a demo public value h and private x.", weakness="Reusing k links messages: one known plaintext reveals others. The same mistake in ECDSA leaked Sony's PS3 signing key.",
    encrypt=lambda t, p=PRIME, g=G, h=H_EX, k=99991, x=None: eg_e(t, p, g, h, k), decrypt=lambda t, p=PRIME, g=G, h=H_EX, k=99991, x=424242: eg_d(t, p, x),
    key={"p": PRIME, "g": G, "h": H_EX, "k": 99991, "x": 424242}, example="Fresh randomness", params=[Param("p", "Prime p", "text"), Param("g", "Generator g", "text"), Param("h", "Public h", "text"), Param("k", "Ephemeral k", "text"), Param("x", "Private x", "text")], demo_attack=M.elgamal_reuse, modern=True)

# Toy curve y^2 = x^3 + 497x + 1768 over F_9739: small enough to walk the whole group.
EC_P, EC_A, EC_G = 9739, 497, (1804, 5368)
EC_B = 1768


def ec_add(p1, p2):
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    if p1[0] == p2[0] and (p1[1] + p2[1]) % EC_P == 0:
        return None
    m = (3 * p1[0] ** 2 + EC_A) * pow(2 * p1[1], -1, EC_P) if p1 == p2 else (p2[1] - p1[1]) * pow(p2[0] - p1[0], -1, EC_P)
    x = (m * m - p1[0] - p2[0]) % EC_P
    return x, (m * (p1[0] - x) - p1[1]) % EC_P


def ec_mul(k, pt):
    r = None
    while k:
        if k & 1:
            r = ec_add(r, pt)
        pt, k = ec_add(pt, pt), k >> 1
    return r


def _ecdh(a, b):
    return hashlib.sha256(str(ec_mul(int(a) * int(b), EC_G)).encode()).digest()


def ec_e(t, a=1829, b=4177):
    return xor_bytes(t.encode(), _ecdh(a, b)).hex()


def ec_d(t, a=1829, b=4177):
    return xor_bytes(bytes.fromhex(t), _ecdh(a, b)).decode(errors="replace")


add(id="ecdh", name="Elliptic-curve Diffie-Hellman", family=FAM, era="Miller and Koblitz, 1985", summary="Diffie-Hellman on points of a curve.",
    how="Points on y^2 = x^3 + ax + b form a group. Multiplying a point by a secret is easy; undoing it is the elliptic-curve discrete log. This demo uses a tiny curve over p = 9739.",
    weakness="Small curves are searched directly, as shown. Real curves use about 256 bits. Quantum computers running Shor's algorithm would break this and RSA, hence post-quantum standards.", encrypt=ec_e, decrypt=ec_d, key={"a": 1829, "b": 4177}, example="Points on a curve", params=[Param("a", "Alice's secret", "int"), Param("b", "Bob's secret", "int")],
    demo_attack=lambda s: M.ecdlp(s, ec_mul, EC_G), modern=True)


SP = 2147483647


def _shamir(secret, k, n, seed):
    import random
    r = random.Random(seed)
    coef = [secret] + [r.randrange(SP) for _ in range(k - 1)]
    return [(x, sum(c * pow(x, i, SP) for i, c in enumerate(coef)) % SP) for x in range(1, n + 1)]


def _lagrange(shares):
    s = 0
    for xi, yi in shares:
        num = den = 1
        for xj, _ in shares:
            if xj != xi:
                num = num * -xj % SP
                den = den * (xi - xj) % SP
        s = (s + yi * num * pow(den, -1, SP)) % SP
    return s


def sh_e(t, k=3, n=5, seed=1):
    v = int.from_bytes(t.encode()[:3], "big")
    return " ".join(f"{x}:{y}" for x, y in _shamir(v, int(k), int(n), int(seed)))


def sh_d(t, k=3, n=5, seed=1):
    s = _lagrange([tuple(map(int, p.split(":"))) for p in t.split()[: int(k)]])
    return s.to_bytes(3, "big").lstrip(b"\0").decode(errors="replace")


def sh_demo(seed):
    shares = _shamir(424242, 3, 5, seed)
    wrong = _lagrange(shares[:2])
    right = _lagrange(shares[:3])
    return {"kind": "modern", "title": "Too few shares reveal nothing", "steps": [f"Five shares of a secret, any three needed: {shares}", f"Interpolating with two shares gives a meaningless {wrong}.", f"Three shares give the true secret, {right}.", "With fewer than k shares, every possible secret remains equally likely, so this is information-theoretically secure."], "recovered": str(right), "truth": "424242", "success": right == 424242}


add(id="shamir", name="Shamir secret sharing", family="Public key", era="Adi Shamir, 1979", summary="Split a secret so any k of n shares recover it.",
    how="Hide the secret as the constant term of a random degree k-1 polynomial. Each share is a point on the curve. Up to three bytes are shared in this demo.", weakness="None if used correctly: fewer than k shares carry zero information. Implementations fail through bad randomness or cheating participants.",
    encrypt=sh_e, decrypt=sh_d, key={"k": 3, "n": 5, "seed": 1}, example="Key", params=[Param("k", "Threshold k", "int"), Param("n", "Shares n", "int"), Param("seed", "Random seed", "int")], demo_attack=sh_demo, modern=True)
