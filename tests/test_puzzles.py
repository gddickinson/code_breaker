"""The browser puzzle solvers must produce valid solutions."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parent.parent / "codebreaker/web/static/puzzles_engine.js"


def node(body):
    if not shutil.which("node"):
        pytest.skip("node not installed")
    return json.loads(subprocess.run(["node", "-e", f"const P=require({json.dumps(str(ENGINE))});let seed=9;const R=()=>{{seed=(seed*1664525+1013904223)%4294967296;return seed/4294967296}};{body}"], capture_output=True, text=True, check=True).stdout)


def test_lights_out_solutions_clear_the_board():
    assert node("let ok=0;for(let t=0;t<40;t++){let g=Array(25).fill(0);for(let i=0;i<15;i++)g=P.lightsApply(g,5,Math.floor(R()*25));const s=P.lightsOutSolve(g,5);s.forEach((v,i)=>{if(v)g=P.lightsApply(g,5,i)});if(g.every(v=>!v))ok++}console.log(JSON.stringify(ok))") == 40


def test_sliding_solutions_reach_goal_by_legal_moves():
    r = node("const out=[];for(let t=0;t<20;t++){const p=P.slidingSolve(P.slidingScramble(R,80));out.push([p.at(-1).join(''),p.slice(1).every((s,i)=>{const a=p[i],d=[];s.forEach((v,j)=>{if(v!==a[j])d.push(j)});return d.length===2})])}console.log(JSON.stringify(out))")
    assert all(a == "123456780" and b for a, b in r)


def test_hanoi_length():
    assert node("console.log(JSON.stringify(P.hanoi(7).length))") == 127


def test_queens_are_non_attacking():
    assert node("let ok=true;for(let n=4;n<=12;n++){const c=P.nQueens(n).col;for(let i=0;i<n;i++)for(let j=0;j<i;j++)if(c[i]===c[j]||Math.abs(c[i]-c[j])===i-j)ok=false}console.log(JSON.stringify(ok))")


def test_knights_tour_is_complete():
    r = node("let ok=0,total=0;for(let y=0;y<8;y++)for(let x=0;x<8;x++){const p=P.knightsTour(8,x,y);total++;const set=new Set(p.map(q=>q.join()));const legal=p.slice(1).every((q,i)=>{const a=Math.abs(q[0]-p[i][0]),b=Math.abs(q[1]-p[i][1]);return a*b===2});if(p.length===64&&set.size===64&&legal)ok++}console.log(JSON.stringify([ok,total]))")
    assert r[1] == 64 and r[0] >= 60


def test_mastermind_always_finds_the_code():
    worst = node("let w=0;for(let t=0;t<60;t++){const s=[0,1,2,3].map(()=>Math.floor(R()*6));const log=P.mmSolve(s);if(log.at(-1).f!==40)w=99;w=Math.max(w,log.length)}console.log(JSON.stringify(w))")
    assert worst <= 7


def test_nonogram_recovers_a_picture():
    assert node("const pic=['0110110','1111111','1111111','1111111','0111110','0011100','0001000'].map(r=>[...r].map(Number));const rows=pic.map(P.nonogramClues),cols=pic[0].map((_,x)=>P.nonogramClues(pic.map(r=>r[x])));const s=P.nonogramSolve(rows,cols);console.log(JSON.stringify(s.complete&&JSON.stringify(s.grid)===JSON.stringify(pic)))")


def cube(body):
    p = ENGINE.with_name("cube_engine.js")
    if not shutil.which("node"):
        pytest.skip("node not installed")
    return json.loads(subprocess.run(["node", "-e", f"const C=require({json.dumps(str(p))});{body}"], capture_output=True, text=True, check=True).stdout)


def test_cube_guide_algorithms():
    """Last-layer moves must leave the two lower layers intact; repeated cycles must return home."""
    apply = "const run=(s,a)=>a.split(' ').forEach(m=>C.applyMove(s,m));"
    for alg in ("F R U R' U' F'", "R U R' U R U2 R'", "U R U' L' U R' U' L"):
        assert cube(apply + f"const s=C.newCube();run(s,{json.dumps(alg)});const low=x=>x.pos[1]<1&&x.n[1]!==1;console.log(JSON.stringify(s.filter(low).every(x=>C.facelets(C.newCube())[0]&&(x.color===(x.n[0]===1?'R':x.n[0]===-1?'L':x.n[2]===1?'F':x.n[2]===-1?'B':'D')))))")
    assert cube(apply + "const s=C.newCube();for(let i=0;i<6;i++)run(s,\"R' D' R D\");console.log(JSON.stringify(C.facelets(s)===C.SOLVED_CUBE))")
    assert cube(apply + "const s=C.newCube();for(let i=0;i<3;i++)run(s,\"U R U' L' U R' U' L\");console.log(JSON.stringify(C.facelets(s)===C.SOLVED_CUBE))")
    assert cube(apply + "const s=C.newCube();for(let i=0;i<6;i++)run(s,\"R U R' U'\");console.log(JSON.stringify(C.facelets(s)===C.SOLVED_CUBE))")
    for alg in ("U R U' R' U' F' U F", "U' L' U L U F U' F'"):
        assert cube(apply + f"const s=C.newCube();run(s,{json.dumps(alg)});console.log(JSON.stringify(s.filter(x=>x.n[1]===-1).every(x=>x.color==='D')))")


def test_lights_out_chase_table_solves_boards():
    """The published last-row table in the guide must clear every solvable random board."""
    tab = {r[0]: r[1] for r in json.loads((ENGINE.with_name("tutorials.json")).read_text())[2]["table"][1:]}
    r = node(f"""const T={json.dumps(tab)};const chase=g=>{{for(let y=1;y<5;y++)for(let x=0;x<5;x++)if(g[(y-1)*5+x])g=P.lightsApply(g,5,y*5+x);return g}};
    let ok=0;for(let t=0;t<200;t++){{let g=Array(25).fill(0);for(let i=0;i<25;i++)if(R()<0.5)g=P.lightsApply(g,5,i);g=chase(g);const row=g.slice(20).join('');if(row!=='00000'){{[...T[row]].forEach((v,i)=>{{if(v==='1')g=P.lightsApply(g,5,i)}});g=chase(g)}}if(g.every(v=>!v))ok++}}console.log(JSON.stringify(ok))""")
    assert r == 200


def test_every_guide_step_has_a_diagram():
    data = json.loads(ENGINE.with_name("tutorials.json").read_text())
    p = ENGINE.with_name("guide_diagrams.js")
    if not shutil.which("node"):
        pytest.skip("node not installed")
    out = json.loads(subprocess.run(["node", "-e", f"const P=require({json.dumps(str(ENGINE))});global.lightsApply=P.lightsApply;const D=require({json.dumps(str(p))}).diagramsFor();console.log(JSON.stringify(Object.fromEntries(Object.entries(D).map(([k,v])=>[k,v.map(x=>x.includes('undefined'))]))))"], capture_output=True, text=True, check=True).stdout)
    for t in data:
        assert len(out[t["id"]]) == len(t["steps"]), t["id"]
        assert not any(out[t["id"]]), t["id"]
