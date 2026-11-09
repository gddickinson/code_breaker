"""Browser computer-system simulations must agree with standard implementations."""
import json
import random
import shutil
import subprocess
from pathlib import Path

import pytest
from Crypto.Cipher import AES

from codebreaker.ciphers.modern_symmetric import sdes_block

ENGINE = Path(__file__).resolve().parent.parent / "codebreaker/web/static/sim_crypto_engine.js"


def node(script):
    if not shutil.which("node"):
        pytest.skip("node not installed")
    return json.loads(subprocess.run(["node", "-e", f"const S=require({json.dumps(str(ENGINE))});{script}"], capture_output=True, text=True, check=True).stdout)


def test_aes_matches_library_and_fips_vector():
    key = bytes(range(16))
    assert node("console.log(JSON.stringify(S.hex(S.aesEncrypt([...S.unhex('00112233445566778899aabbccddeeff')],[...S.unhex('000102030405060708090a0b0c0d0e0f')]))))") == "69c4e0d86a7b0430d8cdb78070b4c55a"
    r = random.Random(5)
    for _ in range(25):
        k, b = r.randbytes(16), r.randbytes(16)
        got = node(f"console.log(JSON.stringify(S.hex(S.aesEncrypt([...S.unhex('{b.hex()}')],[...S.unhex('{k.hex()}')]))))")
        assert got == AES.new(k, AES.MODE_ECB).encrypt(b).hex()
    assert key


def test_sdes_matches_python():
    pairs = [(v, k) for v in (0, 1, 65, 179, 255) for k in (0, 642, 1023)]
    got = node(f"console.log(JSON.stringify({json.dumps(pairs)}.map(([v,k])=>S.sdesTrace(v,k).out)))")
    assert got == [sdes_block(v, k) for v, k in pairs]


def test_modpow_steps():
    assert node("console.log(JSON.stringify(S.modPowSteps(65,17,3233).value))") == pow(65, 17, 3233)


def test_colossus_peak_finds_the_setting():
    wheel = [random.Random(3).randint(0, 1) for _ in range(41)]
    wheel = [random.Random(i + 9).randint(0, 1) for i in range(41)]
    hits = node(f"const w={json.dumps(wheel)};let h=0;for(let t=0;t<41;t++){{const c=S.colossusCount(S.colossusTape(w,t,2400,0.62,41+t),w);if(c.indexOf(Math.max(...c))===t)h++}};console.log(JSON.stringify(h))")
    assert hits >= 38


def test_lsb_steganography_round_trip():
    got = node("const p=new Uint8Array(3000).map((_,i)=>i%251);const o=S.lsbEmbed(p,'Rendez-vous à minuit');const d=o.reduce((a,v,i)=>Math.max(a,Math.abs(v-p[i])),0);console.log(JSON.stringify([S.lsbExtract(o),d]))")
    assert got == ["Rendez-vous à minuit", 1]
