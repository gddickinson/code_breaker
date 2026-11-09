"""Worked attacks on weak or misused modern cryptography. All run against local toy targets.

Each function takes a seed and returns {kind, title, steps, recovered, truth, success}.
"""
import hashlib
import math
import random
import time

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from sympy import factorint, integer_nthroot

SAMPLE = "Modern ciphers fail through misuse far more often than through mathematics, and careful engineers know this well."


def out(title, steps, recovered, truth):
    return {"kind": "modern", "title": title, "steps": steps, "recovered": str(recovered), "truth": str(truth), "success": recovered == truth}


def _printable_score(b):
    good = b" etaoinshrdluETAOINSHRDLU"
    return sum(c in good for c in b) - 5 * sum(c < 32 or c > 126 for c in b)


def repeating_xor(seed, xor):
    r = random.Random(seed)
    key = bytes(r.choice(b"ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(r.randint(3, 9)))
    ct = xor((SAMPLE * 4).encode(), key)
    ham = lambda a, b: sum(bin(x ^ y).count("1") for x, y in zip(a, b))
    dist = {k: sum(ham(ct[i * k:(i + 1) * k], ct[(i + 1) * k:(i + 2) * k]) / k for i in range(12)) for k in range(2, 16)}
    k = min(dist, key=dist.get)
    rec = bytes(max(range(256), key=lambda g: _printable_score(bytes(c ^ g for c in ct[i::k]))) for i in range(k))
    return out("Hamming distance, then single-byte XOR per column", [f"Secret key has {len(key)} bytes.", f"Lowest normalised Hamming distance at length {k}.", "Each column is a single-byte XOR, solved by letter frequency."], xor(ct, rec).decode(errors="replace")[:60], (SAMPLE * 4)[:60])


def two_time_pad(seed, xor):
    r = random.Random(seed)
    pad_bytes = r.randbytes(64)
    a, b = b"THE AGENT WILL MEET THE COURIER AT THE BRIDGE", b"SEND ALL THE MONEY TO THE ACCOUNT IN GENEVA ."
    ca, cb = xor(a, pad_bytes), xor(b, pad_bytes)
    x = bytes(p ^ q for p, q in zip(ca, cb))
    rec = bytes(p ^ q for p, q in zip(x, a))
    return out("Pad reuse and crib-dragging", ["The XOR of two ciphertexts cancels the pad: C1 ^ C2 = P1 ^ P2.", f"That XOR begins {x[:8].hex()}, independent of the key.", "Sliding a likely word along it reveals readable text in the other message. Here a full crib of message 1 reveals message 2."], rec.decode(), b.decode())


def rc4_bias(seed, stream):
    r = random.Random(seed)
    n = 30000
    zeros = sum(stream(r.randbytes(16), 2)[1] == 0 for _ in range(n))
    ratio = zeros / n * 256
    return out("Second output byte is biased towards zero", [f"Across {n} random keys, second byte was 0 in {zeros} cases.", f"That is {ratio:.2f} times the uniform rate. Mantin and Shamir predicted 2 times.", "A repeated plaintext encrypted under many keys therefore leaks its second byte."], ratio > 1.5, True)


def sdes_brute(seed, block):
    r = random.Random(seed)
    key = r.randrange(1024)
    pairs = [(p, block(p, key)) for p in [0x41, 0x7a, 0x13]]
    t = time.time()
    cands = [k for k in range(1024) if all(block(p, k) == c for p, c in pairs)]
    return out("Exhaustive search of 1,024 keys", [f"Secret key is {key}.", f"Three known plaintext pairs leave {len(cands)} candidate key(s), in {time.time() - t:.3f}s."], key in cands, True)


def _noparity(k):
    return bytes(b & 0xFE for b in k) if k else None


def des_reduced(seed, DES):
    r = random.Random(seed)
    key = bytes.fromhex("133457799bb00000")[:5] + bytes([r.randrange(16) << 4, r.randrange(256), r.randrange(256)])
    pt = b"KNOWNTXT"
    ct = DES.new(key, DES.MODE_ECB).encrypt(pt)
    t = time.time()
    found = None
    tried = 0
    for v in range(2**20):
        tried += 1
        k = key[:5] + bytes([(v >> 16) << 4, (v >> 8) & 255, v & 255])
        if DES.new(k, DES.MODE_ECB).encrypt(pt) == ct:
            found = k
            break
    dt = max(time.time() - t, 1e-6)
    rate = tried / dt
    years = 2**55 / rate / 86400 / 365
    return out("Reduced-key brute force with extrapolation", [f"Searched a 20-bit unknown part: {tried:,} keys at {rate:,.0f} keys per second.", f"Single-threaded, the full 2^55 average search would take about {years:,.0f} years here. Special hardware did it in days in 1998.", "DES ignores the low bit of each key byte, so keys are compared without parity bits."], _noparity(found), _noparity(key)) | {"recovered": found.hex() if found else "", "truth": key.hex()}


def meet_in_middle(seed, block):
    r = random.Random(seed)
    k1, k2 = r.randrange(1024), r.randrange(1024)
    pairs = [(p, block(block(p, k1), k2)) for p in (0x41, 0x7a, 0xc3, 0x09)]
    table = {}
    for a in range(1024):
        table.setdefault(tuple(block(p, a) for p, _ in pairs), []).append(a)
    hits = []
    for b in range(1024):
        mid = tuple(block(c, b, True) for _, c in pairs)
        hits += [(a, b) for a in table.get(mid, [])]
    return out("Meet in the middle on double encryption", [f"Double S-DES has 2^20 key pairs, but we only compute 2 x 2^10 halves.", f"Matching the middle values left {len(hits)} candidate pair(s).", "This is why two encryptions give about one extra bit of security, and why 3DES uses three."], (k1, k2) in hits, True)


def ecb_suffix(seed):
    r = random.Random(seed)
    key = r.randbytes(16)
    secret = b"The vault code is 8-4-1-9."
    oracle = lambda p: AES.new(key, AES.MODE_ECB).encrypt(pad(p + secret, 16))
    rec = b""
    queries = 0
    for i in range(len(secret)):
        prefix = b"A" * (15 - i % 16)
        idx = len(prefix + rec) // 16
        target = oracle(prefix)[idx * 16:(idx + 1) * 16]
        queries += 1
        for g in range(256):
            queries += 1
            if oracle(prefix + rec + bytes([g]))[idx * 16:(idx + 1) * 16] == target:
                rec += bytes([g])
                break
    return out("Byte-at-a-time chosen-prefix decryption", ["We control a prefix placed before a secret, under an unknown key.", "Pad the prefix so that one unknown byte sits at the end of a block, then try all 256 guesses for a matching block.", f"Recovered the secret in {queries} oracle queries, without the key."], rec.decode(), secret.decode())


def padding_oracle(seed):
    r = random.Random(seed)
    key, iv = r.randbytes(16), r.randbytes(16)
    secret = b"Padding oracles need no key."
    ct = AES.new(key, AES.MODE_CBC, iv).encrypt(pad(secret, 16))
    calls = [0]

    def oracle(prev, block):
        calls[0] += 1
        try:
            unpad(AES.new(key, AES.MODE_CBC, bytes(prev)).decrypt(bytes(block)), 16)
            return True
        except ValueError:
            return False

    blocks = [iv] + [ct[i:i + 16] for i in range(0, len(ct), 16)]
    rec = b""
    for b in range(1, len(blocks)):
        inter = bytearray(16)
        for pos in range(15, -1, -1):
            n = 16 - pos
            for g in range(256):
                mod = bytearray(16)
                mod[pos] = g
                for j in range(pos + 1, 16):
                    mod[j] = inter[j] ^ n
                if oracle(mod, blocks[b]):
                    if pos == 15:  # rule out an accidental longer padding
                        mod[14] ^= 1
                        if not oracle(mod, blocks[b]):
                            continue
                    inter[pos] = g ^ n
                    break
        rec += bytes(x ^ y for x, y in zip(inter, blocks[b - 1]))
    return out("Vaudenay's padding oracle", ["The server only says valid or invalid padding.", "Tamper with the previous block until the last byte decrypts to valid padding, revealing the intermediate byte.", f"Recovered every block in {calls[0]} queries, with no key."], unpad(rec, 16).decode(), secret.decode())


def _reuse(a, b, ca, cb, title):
    x = bytes(p ^ q for p, q in zip(ca, cb))
    rec = bytes(p ^ q for p, q in zip(x, a))
    return out(title, ["Two messages used the same key and nonce.", f"C1 ^ C2 = P1 ^ P2: {x[:8].hex()}...", "Knowing or guessing one message reveals the other."], rec.decode(), b.decode())


MSG_A, MSG_B = b"Transfer ten thousand to account 4471 today", b"The password for the backup server is swift"


def nonce_reuse(seed, cls):
    r = random.Random(seed)
    k, n = r.randbytes(16), r.randbytes(8)
    enc = lambda m: cls.new(k, cls.MODE_CTR, nonce=n).encrypt(m)
    return _reuse(MSG_A, MSG_B, enc(MSG_A), enc(MSG_B), "CTR nonce reuse")


def nonce_reuse_cc(seed, cls):
    r = random.Random(seed)
    k, n = r.randbytes(32), r.randbytes(8)
    enc = lambda m: cls.new(key=k, nonce=n).encrypt(m)
    return _reuse(MSG_A, MSG_B, enc(MSG_A), enc(MSG_B), "ChaCha20 nonce reuse")


def gcm_tamper(seed, cls):
    r = random.Random(seed)
    k, n = r.randbytes(16), r.randbytes(12)
    c, tag = cls.new(k, cls.MODE_GCM, nonce=n).encrypt_and_digest(b"Pay Alice 100")
    bad = bytearray(c)
    bad[-1] ^= 1
    try:
        cls.new(k, cls.MODE_GCM, nonce=n).decrypt_and_verify(bytes(bad), tag)
        res = False
    except ValueError:
        res = True
    return out("Tampering is detected", ["A flipped ciphertext bit would silently change CTR plaintext.", "GCM's tag fails verification, so the forged message is rejected."], res, True)


def hash_dictionary(seed):
    r = random.Random(seed)
    words = ["password", "letmein", "dragon", "monkey", "sunshine", "princess", "qwerty", "trustno1", "shadow", "master"]
    secret = r.choice(words)
    target = hashlib.md5(secret.encode()).hexdigest()
    found = next((w + str(i) for w in words for i in [""] + list(range(10)) if hashlib.md5((w + str(i)).encode()).hexdigest() == target), None)
    return out("Dictionary attack on an unsalted hash", [f"Stored hash: {target}", "Hash every candidate password and compare. Salts and slow functions such as Argon2 exist to make this expensive."], found, secret)


def timing_compare(seed):
    r = random.Random(seed)
    secret = "".join(r.choice("0123456789abcdef") for _ in range(8))
    calls = [0]

    def naive(guess):  # counts comparisons, a deterministic stand-in for measured time
        steps = 0
        for a, b in zip(guess, secret):
            steps += 1
            calls[0] += 1
            if a != b:
                return steps
        return steps + 1

    known = ""
    for i in range(8):
        known += max("0123456789abcdef", key=lambda c: naive((known + c).ljust(8, "?")))
    return out("Timing side channel on tag comparison", ["An early-exit comparison takes longer when more leading characters match.", "We count steps here to simulate the timing signal.", f"Each character is recovered independently: {calls[0]} comparisons instead of 16^8.", "Use hmac.compare_digest."], known, secret)


def rsa_suite(seed):
    r = random.Random(seed)
    from sympy import randprime
    steps, ok = [], True
    p, q = randprime(2**31, 2**32), randprime(2**31, 2**32)
    n, e = p * q, 65537
    f = factorint(n)
    steps.append(f"1. Factoring: a 64-bit n = {n} factors to {sorted(f)} in moments. Real keys use at least 2048 bits.")
    ok &= sorted(f) == sorted([p, q])
    p, q = randprime(2**255, 2**256), randprime(2**255, 2**256)
    n = p * q
    phi = (p - 1) * (q - 1)
    while True:
        d = r.randrange(2**60, 2**61) | 1
        if math.gcd(d, phi) == 1:
            break
    e = pow(d, -1, phi)
    got = _wiener(e, n)
    steps.append(f"2. Wiener: a 61-bit private d under a 512-bit n falls to continued fractions of e/n. Recovered d matches: {got == d}.")
    ok &= got == d
    m = int.from_bytes(b"broadcast secret", "big")
    from sympy import randprime as rp
    ns = [rp(2**127, 2**128) * rp(2**127, 2**128) for _ in range(3)]
    cs = [pow(m, 3, x) for x in ns]
    from sympy.ntheory.modular import crt
    root, exact = integer_nthroot(int(crt(ns, cs)[0]), 3)
    steps.append(f"3. Hastad: the same message to three recipients with e=3 unpadded. CRT gives m^3 exactly, and the cube root gives '{root.to_bytes(16, 'big').decode()}'.")
    ok &= exact and root == m
    n = rp(2**127, 2**128) * rp(2**127, 2**128)
    e1, e2 = 17, 65537
    c1, c2 = pow(m, e1, n), pow(m, e2, n)
    a = pow(e1, -1, e2)
    b = (a * e1 - 1) // e2
    rec = pow(c1, a, n) * pow(pow(c2, -1, n), b, n) % n
    steps.append(f"4. Common modulus: one n with two coprime exponents gives the message without any private key. Match: {rec == m}.")
    ok &= rec == m
    return out("Four attacks on weak RSA", steps, ok, True)


def _wiener(e, n):
    conv, a, b = [], e, n
    h0, h1, k0, k1 = 0, 1, 1, 0
    while b:
        q = a // b
        h0, h1 = h1, q * h1 + h0
        k0, k1 = k1, q * k1 + k0
        a, b = b, a - q * b
        conv.append((h1, k1))
    for k, d in conv:
        if k and (e * d - 1) % k == 0:
            phi = (e * d - 1) // k
            s = n - phi + 1
            disc = s * s - 4 * n
            if disc >= 0:
                root, exact = integer_nthroot(disc, 2)
                if exact:
                    return d
    return None


def dlog_bsgs(seed):
    r = random.Random(seed)
    p, g = 2147483647, 7
    x = r.randrange(2, p - 1)
    h = pow(g, x, p)
    m = math.isqrt(p) + 1
    table = {pow(g, j, p): j for j in range(m)}
    factor = pow(g, -m, p)
    y, got = h, None
    for i in range(m):
        if y in table:
            got = i * m + table[y]
            break
        y = y * factor % p
    return out("Baby-step giant-step on a 31-bit group", [f"Public value h = g^x = {h}.", f"Build {m:,} baby steps, then walk giant steps, for about 2*sqrt(p) work instead of p.", "Real groups use at least 2048 bits, or elliptic curves."], got, x)


def elgamal_reuse(seed):
    r = random.Random(seed)
    p, g, x, k = 2147483647, 7, r.randrange(2, 10**9), r.randrange(2, 10**9)
    h = pow(g, x, p)
    m1, m2 = 123456, 987654
    s = pow(h, k, p)
    c1, c2 = m1 * s % p, m2 * s % p
    rec = c2 * pow(c1, -1, p) * m1 % p
    return out("ElGamal ephemeral key reuse", ["Two ciphertexts share one k, so the same mask multiplies both.", "c2 / c1 = m2 / m1, so one known message reveals the other, with no private key."], rec, m2)


def ecdlp(seed, mul, gen):
    r = random.Random(seed)
    secret = r.randrange(2, 8000)
    target = mul(secret, gen)
    pt, k, found = gen, 1, None
    from ..ciphers.modern_public import ec_add
    while k < 20000:
        if pt == target:
            found = k
            break
        pt, k = ec_add(pt, gen), k + 1
    return out("Walking a tiny elliptic curve", [f"Public point: {target}.", f"Stepped through the group and found the secret after {found} additions.", "A 256-bit curve would need about 2^128 steps even with the best known classical attack."], mul(found, gen), target) | {"recovered": str(found), "truth": str(secret)}
