"""Fetch each community link once and save which ones respond."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINKS = [
 ("Contests and challenges","MysteryTwister","https://mysterytwister.org/","Graded cipher challenges from easy to very hard."),
 ("Contests and challenges","CryptoHack","https://cryptohack.org/","Modern cryptography challenges and lessons."),
 ("Contests and challenges","CTFtime","https://ctftime.org/","Calendar and rankings for capture-the-flag events."),
 ("Contests and challenges","National Cipher Challenge","https://www.cipherchallenge.org/","Annual UK classical-cipher contest. Prizes are for school students, but anyone can follow it."),
 ("Contests and challenges","NSA Codebreaker Challenge","https://nsa-codebreaker.org/","US student contest. Listed for reference only."),
 ("Contests and challenges","picoCTF","https://picoctf.org/","Beginner-friendly practice, aimed at students."),
 ("Contests and challenges","American Cryptogram Association","https://www.cryptogram.org/","Long-running society publishing member cipher puzzles."),
 ("Historical ciphers and open problems","Cipher Mysteries","https://ciphermysteries.com/","Nick Pelling's site on unsolved historical ciphers."),
 ("Historical ciphers and open problems","Klausis Krypto Kolumne","https://scienceblogs.de/klausis-krypto-kolumne/","Klaus Schmeh's blog, including the Top 50 unsolved messages."),
 ("Historical ciphers and open problems","Zodiac Ciphers forum","https://forum.zodiackillerciphers.com/","Active community around the Zodiac and related ciphers."),
 ("Historical ciphers and open problems","Voynich Ninja","https://www.voynich.ninja/","Forum on the Voynich manuscript."),
 ("Historical ciphers and open problems","voynich.nu","https://voynich.nu/","Rene Zandbergen's reference site and transliterations."),
 ("Historical ciphers and open problems","Le Figaro personal ads","https://www.apprendre-en-ligne.net/crypto/Figaro/","Thousands of ads, with an open invitation to propose decryptions."),
 ("Historical ciphers and open problems","r/codes","https://www.reddit.com/r/codes/","Reddit community for help with ciphers."),
 ("Historical ciphers and open problems","Elonka Dunin on Kryptos","https://elonka.com/kryptos/","Long-standing Kryptos resource."),
 ("Research","HistoCrypt conference","https://histocrypt.org/","International conference on historical cryptology."),
 ("Research","DECRYPT project","https://de-crypt.org/","Tools and resources for historical cryptology."),
 ("Research","IACR ePrint Archive","https://eprint.iacr.org/","Open preprints in cryptology."),
 ("Tools","CrypTool","https://www.cryptool.org/","Free cryptography learning software."),
 ("Tools","AZdecrypt","https://github.com/doranchak/azdecrypt","Strong homophonic solver and cipher collection."),
 ("Tools","dCode","https://www.dcode.fr/en","Online cipher and puzzle tools."),
 ("Puzzles","World Cube Association","https://www.worldcubeassociation.org/","Official speedcubing competitions."),
 ("Puzzles","God's Number is 20","https://cube20.org/","The proof that any cube can be solved in 20 moves."),
 ("Puzzles","Kociemba's two-phase algorithm","https://kociemba.org/cube.htm","The cube-solving method used in this app."),
 ("Puzzles","Project Euler","https://projecteuler.net/","Mathematical programming problems."),
 ("Puzzles","Advent of Code","https://adventofcode.com/","Daily programming puzzles each December."),
]
out = []
for cat, name, url, note in LINKS:
    r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-L", "-m", "20", "-A", "Mozilla/5.0 (codebreaker link check)", "-w", "%{http_code}", url], capture_output=True, text=True)
    out.append({"category": cat, "name": name, "url": url, "note": note, "status": r.stdout})
    print(r.stdout, name, flush=True)
(ROOT / "codebreaker/web/static/community.json").write_text(json.dumps(out, indent=0))
