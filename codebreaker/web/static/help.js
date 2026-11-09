/* Help page with app guide and glossary, and the history timeline with one page per event. */
const GLOSSARY = [
  ["Attack", "A method of recovering a message or key without being given the key."], ["Autokey", "A cipher in which the message itself extends the key."], ["Bigram", "A pair of adjacent letters or symbols."],
  ["Block cipher", "A cipher that encrypts fixed-size chunks of data, such as AES."], ["Book cipher", "A cipher in which numbers point to words in a shared text."], ["Brute force", "Trying every possible key."],
  ["Cipher", "A method that changes letters or bits according to a key."], ["Code", "A system that replaces whole words or phrases, usually using a codebook."], ["Control", "A test on a problem with a known answer, used to prove a method works before trusting it."],
  ["Conditional entropy (H2)", "How predictable the next symbol is from the current one. Lower means more predictable."], ["Coverage", "Here, the share of letters in a reading that fall within dictionary words of four or more letters."], ["Crib", "A guessed piece of plaintext used to attack a cipher."],
  ["Depth", "Two or more messages enciphered with the same key."], ["Digraph", "A pair of letters treated as one unit."], ["Diffusion", "Spreading the influence of each plaintext letter across the ciphertext."],
  ["Fractionation", "Splitting letters into smaller parts, such as coordinates, and mixing them."], ["Frequency analysis", "Using how often symbols occur to work out what they mean."], ["Hash", "A one-way fingerprint of data."],
  ["Homophonic cipher", "A substitution giving several symbols to common letters."], ["Index of coincidence (IC)", "The chance two random letters match. About 0.066 in English, 0.038 for random letters."], ["Key", "The secret that controls a cipher."],
  ["Kerckhoffs's principle", "A system should stay secure even if everything except the key is public."], ["Language model", "A statistical or neural estimate of how much text looks like a language."], ["Lead", "A clue worth following that is not a solution."],
  ["Monoalphabetic", "Using one fixed substitution alphabet."], ["Nomenclator", "A historical mix of cipher alphabet and code words."], ["Null", "A meaningless symbol added to confuse. Also, in statistics, the comparison case where no real signal exists."],
  ["One-time pad", "XOR with a truly random key as long as the message, used once."], ["Plaintext and ciphertext", "The original message and its encrypted form."], ["Polyalphabetic", "Changing substitution alphabet during a message."],
  ["Quadgram", "A sequence of four letters. Quadgram scores judge how language-like a text is."], ["Simulated annealing", "A search that accepts some worse moves early on, to avoid getting stuck."], ["Stream cipher", "A cipher that combines data with a generated key stream."],
  ["Substitution", "Replacing symbols while keeping their order."], ["Transposition", "Rearranging symbols while keeping their identity."], ["Unicity distance", "The approximate length of ciphertext needed for one key to be the only sensible answer."], ["z-score", "How many standard deviations a result sits above the comparison cases."]
];
const GUIDE = [
  ["Library", "#/", "Every cipher in the app. Each page explains it, encrypts your text, and runs a real attack."], ["Machines", "#/machines", "Working models, including an Enigma you can type on and a bombe."], ["How It Works", "#/how", "Illustrated, interactive explanations of attacks and computer systems such as AES."], ["Maths", "#/math", "The mathematics of codebreaking, with worked examples."], ["Puzzles", "#/puzzles", "A 3D Rubik's cube with a real solver, and sudoku."], ["Community", "#/community", "Contests, forums and resources."], ["Publications", "#/publications", "A searchable index of academic work."], ["How Secrets Travel", "#/channels", "Hidden messages and transmission technologies over time, with a steganography demo."], ["Workbench", "#/workbench", "Paste any ciphertext for statistics, a guess at its type, and Autobreak."],
  ["Mystery Lab", "#/mysteries", "Case files on real unsolved ciphers and lost scripts."], ["Lead Board", "#/leads", "The database of every code, fact, lead and attempt, with the hunter's live feed."], ["Open Codes", "#/open", "Every code we track that is still unsolved."], ["Solutions", "#/solutions", "What the tools have verified, and which readings are only candidates."], ["History", "#/history", "A timeline of codebreaking, with a page for each key event."], ["Challenge", "#/challenge", "A hidden cipher to break yourself."], ["Translate", "#/translate", "Language detection, word breaks and offline translation."]
];

route(/^\/help$/, async () => {
  view().innerHTML = `<p class="kicker">// HELP</p><h1>Help and glossary</h1><p class="lead">What each part of the app does, how to read its results, and what the terms mean.</p>
    <h2>Around the app</h2><div class="grid">${GUIDE.map(([n, h, d]) => `<a class="card" href="${h}"><b>${n}</b><span>${d}</span></a>`).join("")}</div>
    <h2>How to read a mystery result</h2>
    <p>A claim has to pass three gates before the app calls it readable. An output that fails any of them is not a solution, however convincing it looks.</p>
    <div class="panel"><ol class="steps"><li><b>The control.</b> Can the solver read a message of this exact size and kind when the answer is known? If not, the result is <em>Inconclusive</em>.</li><li><b>The null.</b> Does the real text beat scrambled copies of itself? If not, the result is <em>No evidence</em>.</li><li><b>Reading as language.</b> Does the output contain real words at the rate a true solution would? If not, the result is <em>Structure only</em>: the order is non-random, but nothing has been read.</li></ol></div>
    <p>A <em>Readable candidate</em> still needs a person to read it and a check of whether someone solved it first.</p>
    <h2>Good to know</h2><ul><li>The ciphers here are for learning. Many are deliberately weak, and toy key sizes are used so attacks finish quickly. Do not protect real secrets with them.</li><li>Models labelled teaching models simplify the real machine. The Enigma attack and the bombe assume ring settings of A.</li><li>Latin translations are rough machine drafts from a general multi-language model. They are useful for orientation but not for judging whether a decryption means anything.</li><li>Results and leads are saved in the project, so they persist between sessions.</li></ul>
    <h2>Glossary</h2><label for="g">Filter</label><input id="g" class="filter" placeholder="Search terms"><dl id="gl" class="gloss"></dl>`;
  const draw = () => { const q = $("#g").value.toLowerCase(); $("#gl").innerHTML = GLOSSARY.filter(([t, d]) => `${t} ${d}`.toLowerCase().includes(q)).map(([t, d]) => `<dt>${esc(t)}</dt><dd>${esc(d)}</dd>`).join("") || '<p class="mute">No matching terms.</p>'; };
  $("#g").oninput = draw; draw();
}, "help");

let HISTORY = null;
async function history() { if (!HISTORY) { const r = await fetch("/static/history.json"); HISTORY = (await r.json()).sort((a, b) => a.sort - b.sort); } return HISTORY; }

route(/^\/history$/, async () => {
  const ev = await history();
  const eras = [...new Set(ev.map(e => e.era))];
  view().innerHTML = `<p class="kicker">// TIMELINE</p><h1>A history of codebreaking</h1><p class="lead">Almost four thousand years of secret writing and the people who broke it. Select any event for the story and links to try it yourself.</p>
    <div class="legend era-nav">${eras.map(e => `<a href="#/history" data-era="${esc(e)}">${esc(e)}</a>`).join("")}</div>
    <ol class="timeline">${ev.map(e => `<li data-e="${esc(e.era)}"><a href="#/history/${esc(e.id)}"><time>${esc(e.year)}</time><b>${esc(e.title)}</b><span>${esc(e.summary)}</span><small>${esc(e.era)}</small></a></li>`).join("")}</ol>`;
  document.querySelectorAll("[data-era]").forEach(a => { a.onclick = ev2 => { ev2.preventDefault(); document.querySelector(`.timeline li[data-e="${CSS.escape(a.dataset.era)}"]`).scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "center" }); }; });
}, "history");

route(/^\/history\/([\w-]+)$/, async id => {
  const ev = await history(), i = ev.findIndex(e => e.id === id);
  if (i < 0) { view().innerHTML = "<h1>Event not found</h1>"; return; }
  const e = ev[i], prev = ev[i - 1], next = ev[i + 1];
  view().innerHTML = `<a href="#/history">← Timeline</a><p class="kicker">// ${esc(e.year)}</p><h1>${esc(e.title)}</h1><p><span class="tag">${esc(e.era)}</span></p><p class="lead">${esc(e.summary)}</p>${e.body.map(p => `<p>${esc(p)}</p>`).join("")}
    <h2>In this app</h2><div class="row">${e.links.map(([l, h]) => `<a class="cta" href="${esc(h)}">${esc(l)}</a>`).join("")}</div>
    <h2>Read more</h2><p><a href="https://en.wikipedia.org/wiki/${encodeURI(e.wiki)}" rel="noreferrer">${esc(e.wiki.replace(/_/g, " "))} on Wikipedia</a></p>
    <nav class="eventnav">${prev ? `<a href="#/history/${esc(prev.id)}">← ${esc(prev.title)}</a>` : "<span></span>"}${next ? `<a href="#/history/${esc(next.id)}">${esc(next.title)} →</a>` : ""}</nav>`;
}, "history");
