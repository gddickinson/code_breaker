"""The browser simulators must produce exactly what the Python ciphers produce."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from codebreaker.ciphers import REGISTRY
from codebreaker.ciphers.machines import enigma
from codebreaker.ciphers.polygraphic import pf_e
from codebreaker.ciphers.transposition import _grille_order

ENGINE = Path(__file__).resolve().parent.parent / "codebreaker/web/static/sim_engine.js"
CASES = [("HELLOWORLDTHEQUICKBROWNFOX" * 12, ["I", "II", "III"], "AAA", "AAA", ""), ("ATTACKATDAWN" * 40, ["IV", "II", "V"], "BXK", "ADU", "AV BS CG DL FU HZ"), ("Q" * 700, ["III", "I", "II"], "ZZA", "VEQ", "QW")]


def node(script):
    if not shutil.which("node"):
        pytest.skip("node not installed")
    return json.loads(subprocess.run(["node", "-e", f"const S=require({json.dumps(str(ENGINE))});{script}"], capture_output=True, text=True, check=True).stdout)


@pytest.mark.parametrize("text,rotors,ring,start,plug", CASES)
def test_enigma_matches_python(text, rotors, ring, start, plug):
    spec = json.dumps({"rotors": rotors, "ring": ring, "start": start, "plugboard": plug})
    assert node(f"console.log(JSON.stringify(new S.Enigma({spec}).run({json.dumps(text)})))") == enigma(text, " ".join(rotors), ring, start, plug)


def test_playfair_matches_python():
    msg, key = "HIDE THE GOLD BALLOON UNDER THE OLD STUMP", "PLAYFAIR"
    got = node(f"const q=S.playfairSquare({json.dumps(key)});console.log(JSON.stringify(S.playfairPairs({json.dumps(msg)}).map(([a,b])=>S.playfairStep(q,a,b).out).join('')))")
    assert got == pf_e(msg, key)


def test_vigenere_matches_python():
    got = node("console.log(JSON.stringify(S.vigenereTrace('ATTACK AT DAWN','LEMON').map(x=>x.c).join('')))")
    assert got == REGISTRY["vigenere"].encrypt("ATTACK AT DAWN", key="LEMON")


def test_grille_matches_python():
    key = "012301230"
    got = node(f"let h=S.grilleHoles({json.dumps(key)}),o=[];for(let q=0;q<4;q++){{o=o.concat(h.map(p=>p[0]*6+p[1]).sort((a,b)=>a-b));h=S.grilleRotate(h)}};console.log(JSON.stringify(o))")
    assert got == _grille_order(key)
    assert sorted(got) == list(range(36))


def test_browser_annealer_breaks_a_substitution():
    import numpy as np

    from codebreaker.languages import corpus_text
    from codebreaker.text import letters, similarity, to_ints

    t = to_ints(corpus_text("en"))
    c = np.bincount(t[:-2] * 676 + t[1:-1] * 26 + t[2:], minlength=17576).astype(float)
    table = np.log10((c + 0.3) / c.sum()).round(2).tolist()
    text = letters(corpus_text("en"))[50000:50520]
    key = "QWERTYUIOPASDFGHJKLZXCVBNM"
    ct = [key.index(ch) for ch in text]
    tmp = Path(__file__).parent / "_anneal_fixture.json"
    tmp.write_text(json.dumps({"t": table, "c": ct}))
    try:
        got = node(f"const d=JSON.parse(require('fs').readFileSync({json.dumps(str(tmp))}));let best='',bs=-1e18;for(let s=1;s<=4;s++){{const a=new S.SubAnneal(d.c,Float32Array.from(d.t),45000,s*7919);while(!a.step(5000));if(a.best>bs){{bs=a.best;best=a.text(a.bestKey)}}}};console.log(JSON.stringify(best))")
    finally:
        tmp.unlink()
    assert similarity(got, text) > 0.8


def test_cube_engine_works_with_the_solver():
    import random

    import kociemba

    cube_path = ENGINE.with_name("cube_engine.js")
    if not shutil.which("node"):
        pytest.skip("node not installed")
    run = lambda body: json.loads(subprocess.run(["node", "-e", f"const C=require({json.dumps(str(cube_path))});{body}"], capture_output=True, text=True, check=True).stdout)
    moves = "U R F D L B U' R' F' D' L' B' U2 R2 F2 D2 L2 B2".split()
    assert run("console.log(JSON.stringify(C.facelets(C.newCube())))") == "UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB"
    r = random.Random(4)
    for _ in range(8):
        seq = [r.choice(moves) for _ in range(25)]
        state = run(f"const s=C.newCube();{json.dumps(seq)}.forEach(m=>C.applyMove(s,m));console.log(JSON.stringify(C.facelets(s)))")
        sol = kociemba.solve(state).split()
        assert len(sol) <= 26
        assert run(f"const s=C.newCube();{json.dumps(seq + sol)}.forEach(m=>C.applyMove(s,m));console.log(JSON.stringify(C.facelets(s)))") == "UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB"


def test_sudoku_solver():
    if not shutil.which("node"):
        pytest.skip("node not installed")
    p = "530070000600195000098000060800060003400803001700020006060000280000419005000080079"
    cube_path = ENGINE.with_name("cube_engine.js")
    out = json.loads(subprocess.run(["node", "-e", f"const C=require({json.dumps(str(cube_path))});const g=[...{json.dumps(p)}].map(Number);C.solveSudoku(g);console.log(JSON.stringify(g.join('')))"], capture_output=True, text=True, check=True).stdout)
    assert out == "534678912672195348198342567859761423426853791713924856961537284287419635345286179"


def _node_cube(body):
    return json.loads(subprocess.run(["node", "-e", f"const C=require({json.dumps(str(ENGINE.with_name('cube_engine.js')))});{body}"], capture_output=True, text=True, check=True).stdout)


def test_cube_photo_colours_are_classified():
    if not shutil.which("node"):
        pytest.skip("node not installed")
    js = """const pal={U:[235,235,225],R:[190,30,45],F:[20,160,75],D:[225,200,20],L:[245,120,20],B:[25,85,205]};
    const s=C.newCube();"R U2 F' D L2 B R' F2 U' L D2".split(" ").forEach(m=>C.applyMove(s,m));const f=C.facelets(s);let seed=5;const r=()=>{seed=(seed*1664525+1013904223)%4294967296;return seed/4294967296};
    const samples=[...f].map(l=>{const b=0.75+r()*0.4;return pal[l].map(v=>Math.min(255,Math.round(v*b+(r()-0.5)*18)))});console.log(JSON.stringify([C.classifyCube(samples),f]))"""
    got, want = _node_cube(js)
    assert sum(a == b for a, b in zip(got, want)) >= 52
    assert all(got.count(c) == 9 for c in "URFDLB")


def test_cube_loads_from_facelets():
    if not shutil.which("node"):
        pytest.skip("node not installed")
    assert _node_cube("const s=C.newCube();C.applyMove(s,'R');C.applyMove(s,'U');const f=C.facelets(s);console.log(JSON.stringify(C.facelets(C.cubeFromFacelets(f))===f))")


def test_genetic_code_translation():
    if not shutil.which("node"):
        pytest.skip("node not installed")
    src = ENGINE.with_name("biology.js").read_text()
    code = src[src.index('const BASES'):src.index('route(')]
    out = subprocess.run(["node", "-e", code + "console.log(JSON.stringify([translateDNA('ATGGCCATTGTAATGGGCCGCTGAAAGGGTGCCCGATAG'),translateDNA('UUUAAAGGG')]))"], capture_output=True, text=True, check=True).stdout
    assert json.loads(out) == ["MAIVMGR*KGAR*", "FKG"]
