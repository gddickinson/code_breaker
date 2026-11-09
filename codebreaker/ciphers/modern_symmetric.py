"""Real symmetric primitives, each paired with the classic way it gets broken in practice."""
import hashlib
import hmac as hmaclib
import random

from Crypto.Cipher import AES, ChaCha20, DES, DES3
from Crypto.Util.Padding import pad, unpad

from ..attacks import modern as M
from .base import Param, add

FAM = "Modern symmetric"
MSG = "Modern ciphers fail through misuse far more often than through mathematics."


def _hex(b):
    return b.hex()


def _b(h):
    return bytes.fromhex("".join(h.split()))


def xor_bytes(data, key):
    return bytes(d ^ key[i % len(key)] for i, d in enumerate(data))


def xor_e(t, key="SECRET"):
    return _hex(xor_bytes(t.encode(), key.encode()))


def xor_d(t, key="SECRET"):
    return xor_bytes(_b(t), key.encode()).decode(errors="replace")


add(id="xor", name="Repeating-key XOR", family="Modern stream", era="Computer era", summary="XOR bytes with a repeating key.",
    how="XOR is its own inverse, so one operation both encrypts and decrypts. It is a Vigenere over bytes.", weakness="The same period attack applies. Hamming distance reveals the key length, and each column is single-byte XOR.",
    encrypt=xor_e, decrypt=xor_d, key={"key": "SECRET"}, example=MSG, params=[Param("key", "Key text")], demo_attack=lambda s: M.repeating_xor(s, xor_bytes), modern=True)


def otp_e(t, key=""):
    return _hex(xor_bytes(t.encode(), _b(key)))


def otp_d(t, key=""):
    return xor_bytes(_b(t), _b(key)).decode(errors="replace")


PAD = random.Random(5).randbytes(160).hex()
add(id="otp", name="One-time pad", family="Modern stream", era="Vernam 1917; proven perfect by Shannon 1949", summary="A truly random key as long as the message, used once.",
    how="XOR with a random pad. Shannon proved that the ciphertext reveals nothing except length. The key shown is a fixed demo pad and is not secret.",
    weakness="Unbreakable if used correctly. Reuse a pad, as Soviet operators did, and Project Venona reads your messages by crib-dragging.", encrypt=otp_e, decrypt=otp_d, key={"key": PAD}, example="Perfect secrecy", params=[Param("key", "Pad (hex, at least as long as the message)")], demo_attack=lambda s: M.two_time_pad(s, xor_bytes), modern=True)


def rc4_stream(key, n):
    s, j = list(range(256)), 0
    for i in range(256):
        j = (j + s[i] + key[i % len(key)]) % 256
        s[i], s[j] = s[j], s[i]
    i = j = 0
    out = bytearray()
    for _ in range(n):
        i = (i + 1) % 256
        j = (j + s[i]) % 256
        s[i], s[j] = s[j], s[i]
        out.append(s[(s[i] + s[j]) % 256])
    return bytes(out)


def rc4_e(t, key="Key"):
    d = t.encode()
    return _hex(bytes(a ^ b for a, b in zip(d, rc4_stream(key.encode(), len(d)))))


def rc4_d(t, key="Key"):
    d = _b(t)
    return bytes(a ^ b for a, b in zip(d, rc4_stream(key.encode(), len(d)))).decode(errors="replace")


add(id="rc4", name="RC4", family="Modern stream", era="Rivest 1987; banned from TLS in 2015", summary="A tiny stream cipher once used everywhere.",
    how="A 256-byte state is shuffled by the key and then produces a key stream. It powered WEP and early TLS.", weakness="Early output bytes are biased. WEP's small IVs and related keys let the FMS attack recover keys. Here we show the bias of the second byte towards zero.",
    encrypt=rc4_e, decrypt=rc4_d, key={"key": "Key"}, example="Plaintext", params=[Param("key", "Key text")], demo_attack=lambda s: M.rc4_bias(s, rc4_stream), modern=True)

P10, P8, P4 = [3, 5, 2, 7, 4, 10, 1, 9, 8, 6], [6, 3, 7, 4, 8, 5, 10, 9], [2, 4, 3, 1]
IP, IPI, EP = [2, 6, 3, 1, 4, 8, 5, 7], [4, 1, 3, 5, 7, 2, 8, 6], [4, 1, 2, 3, 2, 3, 4, 1]
S0 = [[1, 0, 3, 2], [3, 2, 1, 0], [0, 2, 1, 3], [3, 1, 3, 2]]
S1 = [[0, 1, 2, 3], [2, 0, 1, 3], [3, 0, 1, 0], [2, 1, 0, 3]]


def _perm(bits, table):
    return [bits[i - 1] for i in table]


def _bits(v, n):
    return [(v >> (n - 1 - i)) & 1 for i in range(n)]


def _val(b):
    r = 0
    for x in b:
        r = r * 2 + x
    return r


def _sdes_keys(key):
    b = _perm(_bits(key, 10), P10)
    l, r = b[:5], b[5:]
    l1, r1 = l[1:] + l[:1], r[1:] + r[:1]
    l2, r2 = l1[2:] + l1[:2], r1[2:] + r1[:2]
    return _perm(l1 + r1, P8), _perm(l2 + r2, P8)


def _fk(b, k):
    l, r = b[:4], b[4:]
    t = [x ^ y for x, y in zip(_perm(r, EP), k)]
    a = S0[t[0] * 2 + t[3]][t[1] * 2 + t[2]]
    c = S1[t[4] * 2 + t[7]][t[5] * 2 + t[6]]
    p = _perm(_bits(a, 2) + _bits(c, 2), P4)
    return [x ^ y for x, y in zip(l, p)] + r


def sdes_block(v, key, decrypt=False):
    k1, k2 = _sdes_keys(key)
    if decrypt:
        k1, k2 = k2, k1
    b = _fk(_perm(_bits(v, 8), IP), k1)
    b = _fk(b[4:] + b[:4], k2)
    return _val(_perm(b, IPI))


def sd_e(t, key=642):
    return _hex(bytes(sdes_block(b, int(key)) for b in t.encode()))


def sd_d(t, key=642):
    return bytes(sdes_block(b, int(key), True) for b in _b(t)).decode(errors="replace")


add(id="sdes", name="Simplified DES", family=FAM, era="Teaching cipher, Schaefer 1996", summary="DES in miniature: 8-bit blocks and a 10-bit key.",
    how="It has the real DES structure: initial permutation, Feistel rounds, expansion, S-boxes and a key schedule, at a size you can follow by hand.", weakness="Only 1,024 keys. Real DES fell the same way in 1998, when the EFF's Deep Crack searched 2^56 keys in days.",
    encrypt=sd_e, decrypt=sd_d, key={"key": 642}, example="Feistel", params=[Param("key", "Key (0-1023)", "int")], demo_attack=lambda s: M.sdes_brute(s, sdes_block), modern=True)


def _block(cls, size):
    def enc(t, key):
        return _hex(cls.new(_b(key), cls.MODE_ECB).encrypt(pad(t.encode(), size)))

    def dec(t, key):
        return unpad(cls.new(_b(key), cls.MODE_ECB).decrypt(_b(t)), size).decode(errors="replace")

    return enc, dec


d_e, d_d = _block(DES, 8)
add(id="des", name="DES", family=FAM, era="NBS standard, 1977", summary="The 56-bit Feistel standard that started public cryptography.",
    how="Sixteen Feistel rounds with S-boxes on 64-bit blocks. The key is 8 bytes in hex, of which 56 bits are effective.", weakness="The 56-bit key is too short. Our demo fixes all but 20 bits so a laptop finishes in seconds, then extrapolates to the full space.",
    encrypt=d_e, decrypt=d_d, key={"key": "133457799bbcdff1"}, example="Deep Crack", params=[Param("key", "Key (16 hex digits)")], demo_attack=lambda s: M.des_reduced(s, DES), modern=True)
t_e, t_d = _block(DES3, 8)
add(id="3des", name="Triple DES", family=FAM, era="1998; retired by NIST in 2023", summary="DES applied three times to extend its life.",
    how="Encrypt-decrypt-encrypt with two or three keys. Double DES was skipped because of the meet-in-the-middle attack.", weakness="Its 64-bit block allows birthday collisions (the Sweet32 attack) after about 2^32 blocks. The demo shows meet-in-the-middle on a toy double cipher.",
    encrypt=t_e, decrypt=t_d, key={"key": "0123456789abcdeffedcba987654321089abcdef01234567"}, example="Three is better than two", params=[Param("key", "Key (48 hex digits)")], demo_attack=lambda s: M.meet_in_middle(s, sdes_block), modern=True)


AES_KEY = "000102030405060708090a0b0c0d0e0f"
NONCE = "a1b2c3d4e5f60718"


def ecb_e(t, key=AES_KEY):
    return _hex(AES.new(_b(key), AES.MODE_ECB).encrypt(pad(t.encode(), 16)))


def ecb_d(t, key=AES_KEY):
    return unpad(AES.new(_b(key), AES.MODE_ECB).decrypt(_b(t)), 16).decode(errors="replace")


P_AES = [Param("key", "Key (32 hex digits)")]
add(id="aes-ecb", name="AES-ECB", family=FAM, era="Rijndael, standardised 2001", summary="AES used block by block with no chaining.",
    how="AES itself remains secure. ECB encrypts each 16-byte block independently, so equal blocks give equal ciphertext.", weakness="Patterns show through, which is the famous ECB penguin. With a chosen prefix, a server can be made to leak a secret suffix one byte at a time.",
    encrypt=ecb_e, decrypt=ecb_d, key={"key": AES_KEY}, example="YELLOW SUBMARINEYELLOW SUBMARINE", params=P_AES, demo_attack=M.ecb_suffix, modern=True)


def cbc_e(t, key=AES_KEY, iv=AES_KEY):
    return _hex(AES.new(_b(key), AES.MODE_CBC, _b(iv)).encrypt(pad(t.encode(), 16)))


def cbc_d(t, key=AES_KEY, iv=AES_KEY):
    return unpad(AES.new(_b(key), AES.MODE_CBC, _b(iv)).decrypt(_b(t)), 16).decode(errors="replace")


add(id="aes-cbc", name="AES-CBC", family=FAM, era="1976 mode; ubiquitous in TLS", summary="Each block is XORed with the previous ciphertext.",
    how="Chaining hides patterns, given an unpredictable IV.", weakness="Unauthenticated CBC falls to Vaudenay's padding-oracle attack: if a server reveals whether padding was valid, every byte can be recovered without the key.",
    encrypt=cbc_e, decrypt=cbc_d, key={"key": AES_KEY, "iv": AES_KEY}, example="Authenticate your ciphertexts", params=P_AES + [Param("iv", "IV (32 hex digits)")], demo_attack=M.padding_oracle, modern=True)


def ctr_e(t, key=AES_KEY, nonce=NONCE):
    return _hex(AES.new(_b(key), AES.MODE_CTR, nonce=_b(nonce)).encrypt(t.encode()))


def ctr_d(t, key=AES_KEY, nonce=NONCE):
    return AES.new(_b(key), AES.MODE_CTR, nonce=_b(nonce)).decrypt(_b(t)).decode(errors="replace")


add(id="aes-ctr", name="AES-CTR", family=FAM, era="Modern stream mode", summary="AES turned into a stream cipher using a counter.",
    how="Encrypt a nonce plus counter to make a key stream, then XOR it with the data.", weakness="Reusing a nonce means reusing a key stream, which becomes a two-time pad.", encrypt=ctr_e, decrypt=ctr_d, key={"key": AES_KEY, "nonce": NONCE}, example="Never reuse a nonce", params=P_AES + [Param("nonce", "Nonce (16 hex digits)")], demo_attack=lambda s: M.nonce_reuse(s, AES), modern=True)


def gcm_e(t, key=AES_KEY, nonce=NONCE):
    c, tag = AES.new(_b(key), AES.MODE_GCM, nonce=_b(nonce)).encrypt_and_digest(t.encode())
    return _hex(c + tag)


def gcm_d(t, key=AES_KEY, nonce=NONCE):
    d = _b(t)
    return AES.new(_b(key), AES.MODE_GCM, nonce=_b(nonce)).decrypt_and_verify(d[:-16], d[-16:]).decode(errors="replace")


add(id="aes-gcm", name="AES-GCM", family=FAM, era="NIST 2007; default in TLS 1.3", summary="Encryption with built-in tamper detection.",
    how="CTR mode plus a polynomial authentication tag. This is what you should actually use.", weakness="A properly used key has no practical attack. Nonce reuse leaks the plaintext XOR and can expose the authentication key. The demo shows tampering being detected.",
    encrypt=gcm_e, decrypt=gcm_d, key={"key": AES_KEY, "nonce": NONCE}, example="Authenticated encryption", params=P_AES + [Param("nonce", "Nonce (16 hex digits)")], demo_attack=lambda s: M.gcm_tamper(s, AES), modern=True)

CH_KEY = AES_KEY * 2


def cc_e(t, key=CH_KEY, nonce=NONCE):
    return _hex(ChaCha20.new(key=_b(key), nonce=_b(nonce)).encrypt(t.encode()))


def cc_d(t, key=CH_KEY, nonce=NONCE):
    return ChaCha20.new(key=_b(key), nonce=_b(nonce)).decrypt(_b(t)).decode(errors="replace")


add(id="chacha20", name="ChaCha20", family="Modern stream", era="Bernstein, 2008; used in TLS and WireGuard", summary="A fast add-rotate-xor stream cipher.",
    how="It mixes a 512-bit state with only additions, rotations and XORs, making it naturally constant-time.", weakness="No practical attack on full rounds. As with all stream ciphers, nonce reuse is catastrophic.", encrypt=cc_e, decrypt=cc_d, key={"key": CH_KEY, "nonce": NONCE}, example="Add rotate xor", params=[Param("key", "Key (64 hex digits)"), Param("nonce", "Nonce (16 hex digits)")], demo_attack=lambda s: M.nonce_reuse_cc(s, ChaCha20), modern=True)


def sha_e(t, algorithm="sha256"):
    return hashlib.new(algorithm, t.encode()).hexdigest()


def hmac_e(t, key="key", algorithm="sha256"):
    return hmaclib.new(key.encode(), t.encode(), algorithm).hexdigest()


add(id="hash", name="Hash functions (MD5, SHA-1, SHA-256, SHA3)", family="Hashes", era="1990s to today", summary="One-way fingerprints of data.",
    how="There is no key and no inverse. A tiny change in input gives an unrelated digest.", weakness="MD5 and SHA-1 have practical collisions. Short or common passwords fall to dictionaries, which is why password storage needs slow, salted hashes.",
    encrypt=sha_e, decrypt=None, key={"algorithm": "sha256"}, example="abc", params=[Param("algorithm", "Algorithm", "choice", ["md5", "sha1", "sha256", "sha512", "sha3_256"])], demo_attack=M.hash_dictionary, modern=True)
add(id="hmac", name="HMAC", family="Hashes", era="Bellare, Canetti, Krawczyk, 1996", summary="A keyed hash proving a message is authentic.",
    how="Two nested hashes with the key mixed in, built to resist the length-extension problem of plain hashes.", weakness="Plain H(key + message) is vulnerable to length extension, and that is why HMAC exists. Comparing tags non-constant-time leaks them through timing.",
    encrypt=hmac_e, decrypt=None, key={"key": "key", "algorithm": "sha256"}, example="The quick brown fox", params=[Param("key", "Key text"), Param("algorithm", "Algorithm", "choice", ["sha256", "sha1", "md5"])], demo_attack=M.timing_compare, modern=True)
