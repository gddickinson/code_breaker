/* Barcodes & QR: the explanations shown above the tools (static text, no server data). */
const BC_FAMILIES = [
  ["Linear (1D)", "Bars and spaces of a few widths, read along one line. A scanner sweeps a laser or reads one row of a camera image. Each has a start and stop pattern, so the code reads in either direction, and a quiet zone of blank space at each end.",
    [["EAN-13 / UPC-A", "Retail products. 13 digits: a prefix for the issuing country or numbering organisation, a company number, a product number and a check digit. Each digit is 7 modules wide, drawn as two bars and two spaces. Books carry an EAN beginning 978 or 979, which is their ISBN-13."],
     ["Code 39", "Letters, digits and a few symbols. Each character is 9 elements, 3 of them wide. Simple and self-checking, so it needs no check digit, but long."],
     ["Code 128", "All 128 ASCII characters in three code sets, one of which packs digit pairs into one symbol. Ends with a check symbol: each symbol's value times its position, plus the start value, modulo 103."],
     ["ITF (Interleaved 2 of 5)", "Digits in pairs: the first digit of a pair is drawn in the bars and the second in the spaces between them. Used on outer cartons as ITF-14."],
     ["Codabar", "Digits and a few symbols between start and stop letters A to D; long used by libraries and blood banks."]]],
  ["Stacked", "Several short rows of a linear code stacked on top of each other, with row indicators so a scanner knows which row it is reading.",
    [["PDF417", "Each codeword is 17 modules wide with 4 bars and 4 spaces (hence the name). Reed–Solomon error correction at levels 0 to 8. On many driving licences, identity cards and boarding passes."]]],
  ["Matrix (2D)", "A grid of square modules, read by a camera in one picture. Fixed patterns let the reader find the symbol, its orientation and its grid; the rest is data protected by Reed–Solomon codes.",
    [["QR Code", "Three square finder patterns in the corners, timing lines between them, alignment patterns on larger versions. Versions 1 to 40, from 21×21 to 177×177 modules (17 + 4 × version). Up to 7,089 digits or 2,953 bytes. Four error-correction levels."],
     ["Micro QR", "One finder pattern and versions M1 to M4, for very small marks; it gives up the highest error-correction level."],
     ["Data Matrix", "An L-shaped solid border to find it and a dotted clock track on the opposite two sides. Very small marks, often laser-etched onto electronic components and medical devices."],
     ["Aztec", "A square bullseye at the centre, so no quiet zone is needed around it. Used on rail and airline tickets read from phone screens."],
     ["MaxiCode", "Hexagonal modules around a bullseye, fixed in size, designed for parcels on fast conveyor belts. The reader here can read it but not make it."]]],
  ["Relatives", "Other ways of putting data where a machine can see it.",
    [["Four-state postal codes", "Each bar is full, ascender, descender or tracker only, so it carries 2 bits. The US Intelligent Mail barcode has 65 bars; the Royal Mail uses a similar four-state code."],
     ["Dot codes", "Grids of dots that can be printed at speed by ink-jet onto cartons and cigarette packs, where solid modules would smear."],
     ["Check digits elsewhere", "Card numbers (Luhn), ISBN-10 (modulo 11) and IBANs (modulo 97) use the same idea as the EAN check digit, without bars. See Theory: Detection."]]],
];

const BC_HISTORY = [
  ["1952", "Norman Woodland and Bernard Silver are granted a US patent for a bullseye barcode, after an idea Woodland drew in sand with his fingers, like Morse code stretched downwards."],
  ["1973", "The US grocery industry adopts the Universal Product Code, designed at IBM by George Laurer."],
  ["1974", "On 26 June, a pack of Wrigley's chewing gum becomes the first product scanned by UPC, at a Marsh supermarket in Troy, Ohio."],
  ["1974", "Code 39 is introduced, the first common code for letters as well as digits."],
  ["1977", "The European Article Number (EAN) extends UPC to 13 digits for use around the world."],
  ["1981", "Code 128 is introduced, covering all ASCII characters."],
  ["1991", "PDF417 is introduced by Symbol Technologies."],
  ["1994", "Denso Wave, a Toyota supplier, releases the QR Code, designed by Masahiro Hara's team to track car parts faster than stacks of linear barcodes allowed. Denso chose not to enforce its patent."],
  ["1995", "The Aztec code is published by Andrew Longacre at Welch Allyn."],
];

const BC_QR_PARTS = [
  ["finder patterns", "#b43ce6", "Three 7×7 squares with a white separator. Their 1:1:3:1:1 dark-light ratio along any line through the centre is how a reader finds the code at any angle and size."],
  ["timing", "#00aae6", "Alternating dark and light modules between the finders, giving the reader the module grid."],
  ["alignment", "#ff7828", "Smaller 5×5 squares (from version 2) that let the reader correct for a curved or tilted surface."],
  ["format information", "#c8c83c", "15 bits, stored twice: the error-correction level and the mask number, protected by a BCH(15,5) code that can fix 3 wrong bits."],
  ["version information", "#3c8c8c", "18 bits, stored twice, from version 7 up: the version, protected by a BCH(18,6) code."],
  ["dark module", "#dc0000", "One module that is always dark."],
  ["data and error correction", "#00a05a", "The message codewords followed by Reed–Solomon check codewords, placed in two-module columns snaking up and down from the bottom right. One of 8 masks is applied to break up large blocks and patterns that look like finders."],
];

function bcInfoHtml() {
  const fam = BC_FAMILIES.map(([name, intro, items]) => `<div class="panel"><h3>${esc(name)}</h3><p>${esc(intro)}</p><ul>${items.map(([n, d]) => `<li><b>${esc(n)}</b>: ${esc(d)}</li>`).join("")}</ul></div>`).join("");
  return `<h2>Kinds of code</h2><div class="biogrid">${fam}</div>
    <h2>How a QR code survives damage</h2><div class="panel"><p>A QR code is Reed–Solomon coded over GF(256): each byte is a symbol, and a block with 2t check bytes can repair any t wrong bytes, or 2t bytes known to be missing. The four levels add more check bytes at the cost of a bigger symbol for the same message.</p>
    ${table(["Level", "Codewords that can be restored", "Typical use"], [["L", "about 7%", "Clean screens and print"], ["M", "about 15%", "The usual default"], ["Q", "about 25%", "Industrial labels"], ["H", "about 30%", "Codes with a logo over them, or rough surfaces"]])}
    <p>Long messages are split into several blocks whose bytes are interleaved across the symbol, so a stain in one place damages a few bytes in each block instead of many in one. This is why a solid blot is survivable but scattered specks are much worse: each speck spoils a different byte, and specks that hit the finders or the format bits can stop the reader before error correction starts. The damage test below measures this.</p>
    <p>See <a href="#/theory/reedsolomon">Theory: Reed–Solomon</a> for the arithmetic, and <a href="#/theory/detection">Theory: Detection</a> for check digits.</p></div>
    <h2>History</h2><div class="panel">${table(["Year", "Event"], BC_HISTORY)}</div>`;
}
