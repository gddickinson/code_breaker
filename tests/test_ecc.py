"""Error-correcting codes shown in the Theory section."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parent.parent / "codebreaker/web/static/ecc_engine.js"


def node(body):
    if not shutil.which("node"):
        pytest.skip("node not installed")
    return json.loads(subprocess.run(["node", "-e", f"const E=require({json.dumps(str(ENGINE))});console.log(JSON.stringify((()=>{{{body}}})()))"], capture_output=True, text=True, check=True).stdout)


def test_hamming_corrects_every_single_error():
    assert node("let ok=0;for(let d=0;d<16;d++)for(let f=-1;f<7;f++){const b=[d>>3&1,d>>2&1,d>>1&1,d&1],c=E.hamming74Encode(b);if(f>=0)c[f]^=1;const o=E.hamming74Decode(c);if(o.data.join('')===b.join('')&&o.syndrome===f+1)ok++}return ok") == 128


def test_reed_solomon_corrects_up_to_t_and_rarely_lies_beyond():
    r = node("const r=E.eccRng(5);let ok=0,lie=0;for(let t=0;t<200;t++){const m=Array.from({length:20},()=>Math.floor(r()*256));for(const k of [5,8]){const c=E.rsEncode(m,10);const used=new Set();while(used.size<k)used.add(Math.floor(r()*c.length));used.forEach(p=>{c[p]^=1+Math.floor(r()*255)});const d=E.rsDecode(c,10);const right=d.ok&&d.data.join()===m.join();if(k===5&&right)ok++;if(k===8&&d.ok&&!right)lie++}}return [ok,lie]")
    assert r[0] == 200 and r[1] <= 10


def test_viterbi_and_ber_ordering():
    assert node("const r=E.eccRng(2),b=Array.from({length:400},()=>r()<.5?1:0);return E.viterbiDecode(E.convEncode(b)).join('')===b.join('')")
    s = node("return E.berCompare(0.02,6000,4).schemes.map(x=>x.ber)")
    assert s[0] > s[1] > s[2] and s[0] > s[3]


def test_detection_checks():
    assert node("return [E.luhnValid('4539 1488 0343 6467'),E.luhnValid('4539 1488 0343 6468'),E.isbn10Valid('0-306-40615-2'),E.isbn10Valid('0-306-40651-2')]") == [True, False, True, False]
    assert node("const m=E.textBits('Hi'),b=[...m];b[3]^=1;b[9]^=1;return E.crcBits(m,E.CRC8).join('')!==E.crcBits(b,E.CRC8).join('')")
