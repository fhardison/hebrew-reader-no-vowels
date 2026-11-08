import hashlib
import json
import re
import unicodedata
import os
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path


TEMPLATE = """
<!DOCTYPE html>
<html dir="rtl" lang="hb">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hebrew Reader</title>
    <link rel="manifest" href="manifest.webmanifest">
    <meta name="theme-color" content="#1d4ed8">
    <link rel="icon" type="image/png" href="icons/icon-192.png">
    <link rel="apple-touch-icon" href="icons/apple-touch-icon.png">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="mobile-web-app-capable" content="yes">
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0 auto;
            max-width: 700px;
            padding: 20px 20px 150px 20px;
            font-size: 1.5em;
        }

        .word-container {
            display: inline-block;
            margin: 8px;
            cursor: pointer;
            touch-action: manipulation;
            -webkit-tap-highlight-color: transparent;
        }

        .word {
            font-weight: normal;
            color: #2c3e50;
            border-bottom: 1px dashed #3498db;
            padding: 2px 4px;
            font-size: 1.15em;
        }

        .word-container.active .word {
            background-color: #dbeafe;
            border-bottom-color: #1d4ed8;
        }

        #info-bar {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: #f8f9fa;
            border-top: 2px solid #3498db;
            padding: 10px 16px;
            padding-bottom: calc(10px + env(safe-area-inset-bottom, 0px));
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2px 12px;
            direction: ltr;
            font-size: 1rem;
            z-index: 200;
            box-sizing: border-box;
        }

        #ib-full  { direction: rtl; font-size: 1.5em; grid-column: 1; grid-row: 1; line-height: 1.4; }
        #ib-gloss { grid-column: 2; grid-row: 1; align-self: center; font-size: 1rem; }
        #ib-lemma { direction: rtl; font-size: 1.1em; grid-column: 1; grid-row: 2; color: #555; line-height: 1.4; }
        #ib-morph { grid-column: 2; grid-row: 2; align-self: start; color: #666; font-size: 0.85rem; padding-top: 2px; }

        @media (max-width: 480px) {
            body { padding-bottom: 180px; }
        }

        #app-bar {
            direction: ltr;
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 6px 12px;
            font-size: 0.85rem;
            color: #555;
            border-bottom: 1px solid #e5e7eb;
            padding-bottom: 8px;
        }
        #app-bar a { color: #1d4ed8; text-decoration: none; font-weight: bold; }
        #app-bar a[hidden], #app-bar button[hidden] { display: none; }
        #ab-status { flex: 1; min-width: 12em; }
        #ab-button {
            font: inherit;
            padding: 4px 12px;
            border: 1px solid #1d4ed8;
            border-radius: 6px;
            background: #fff;
            color: #1d4ed8;
            cursor: pointer;
        }
        #app-bar.ab-attention #ab-status { color: #b45309; font-weight: bold; }
        #app-bar.ab-attention #ab-button { background: #1d4ed8; color: #fff; }
    </style>
</head>
<body>
<nav id="app-bar">
    <a href="./" $homehidden$>&larr; Books</a>
    <span id="ab-status"></span>
    <button id="ab-button" type="button" hidden></button>
</nav>
$body$
    <div id="info-bar">
        <div id="ib-full"></div>
        <div id="ib-gloss"></div>
        <div id="ib-lemma"></div>
        <div id="ib-morph"></div>
    </div>
    <script>
        function expandMorph(code) {
            return code.split('+').map(expandToken).filter(Boolean).join(' + ');
        }

        function expandToken(c) {
            if (!c) return '';
            var p = c[0];

            if (c === 'C') return 'conjunction';
            if (p === 'R') return 'preposition';
            if (c === 'D') return 'adverb';

            if (p === 'T') {
                return ({d:'definite article', e:'existential particle', i:'interrogative',
                         m:'particle', n:'negative particle', o:'object marker',
                         r:'relative', a:'particle', j:'interjection'})[c[1]] || 'particle';
            }

            if (p === 'N') {
                var ntype = ({c:'noun', p:'proper noun', g:'gentilic noun'})[c[1]] || 'noun';
                var nr = c.slice(2);
                return ntype + (nr ? ' ' + expandGNS(nr) : '');
            }

            if (p === 'A') {
                var atype = ({a:'attributive adjective', p:'predicative adjective',
                              s:'substantival adjective', c:'cardinal numeral',
                              o:'ordinal numeral'})[c[1]] || 'adjective';
                var ar = c.slice(2);
                return atype + (ar ? ' ' + expandGNS(ar) : '');
            }

            if (p === 'V') {
                var stems = {q:'Qal', N:'Niphal', p:'Piel', P:'Pual', h:'Hiphil',
                             H:'Hophal', t:'Hithpael', l:'Polel', o:'Polal', e:'Poel'};
                var conjs = {p:'perfect', q:'weqatal', i:'imperfect', w:'wayyiqtol',
                             v:'imperative', j:'jussive', h:'cohortative',
                             r:'participle', s:'passive participle',
                             c:'infinitive construct', a:'infinitive absolute'};
                var stem = stems[c[1]] || c[1];
                var conj = conjs[c[2]] || c[2];
                var vr = c.slice(3);
                var vsuf = vr ? ' ' + (/^[123]/.test(vr) ? vr : expandGNS(vr)) : '';
                return 'verb ' + stem + ' ' + conj + vsuf;
            }

            if (p === 'P') {
                var ptypes = {p:'personal pronoun', d:'demonstrative pronoun',
                              i:'interrogative pronoun', r:'relative pronoun',
                              f:'reflexive pronoun', x:'indefinite pronoun'};
                var pr = c.slice(2);
                return (ptypes[c[1]] || 'pronoun') + (pr ? ' ' + pr : '');
            }

            if (p === 'S') {
                if (c[1] === 'n') return 'nominal suffix';
                var sr = c.slice(2);
                return 'suffix pronoun' + (sr ? ' ' + sr : '');
            }

            return c;
        }

        function expandGNS(rest) {
            var stateMap = {a:'absolute', c:'construct', d:'determined'};
            if (rest.length >= 3) {
                return rest.slice(0, 2) + ' ' + (stateMap[rest[2]] || rest[2]);
            }
            return rest;
        }

        document.addEventListener('DOMContentLoaded', function() {
            var wordContainers = document.querySelectorAll('.word-container');
            var ibFull  = document.getElementById('ib-full');
            var ibGloss = document.getElementById('ib-gloss');
            var ibLemma = document.getElementById('ib-lemma');
            var ibMorph = document.getElementById('ib-morph');

            function clearBar() {
                wordContainers.forEach(function(c) { c.classList.remove('active'); });
                ibFull.textContent = ibGloss.textContent = ibLemma.textContent = ibMorph.textContent = '';
            }

            wordContainers.forEach(function(container) {
                container.addEventListener('click', function(e) {
                    e.stopPropagation();
                    clearBar();
                    container.classList.add('active');
                    var d = container.dataset;
                    ibFull.textContent  = d.full;
                    ibGloss.textContent = d.gloss.replace(/\\+/g, ' ');
                    ibLemma.textContent = d.lemma.replace(/\\+/g, ' ');
                    ibMorph.textContent = expandMorph(d.morph);
                });
            });

            document.addEventListener('click', clearBar);
        });
    </script>
    <script src="pwa.js" defer></script>
</body>
</html>
"""



def remove_hebrew_marks(text):
    # Normalize the text to decompose combined characters
    normalized_text = unicodedata.normalize('NFD', text)
    
    # Define Unicode ranges for Hebrew vowel points, accents, and cantillation marks
    # Vowel points (niqqud): U+05B0–U+05BB
    # Cantillation marks: U+0591–U+05AF
    # Other marks (e.g., rafe, varika): U+05BC–U+05C2
    marks_pattern = r'[\u0591-\u05C2]'
    
    # Remove all specified marks
    clean_text = re.sub(marks_pattern, '', normalized_text)
    
    # Normalize back to composed form
    clean_text = unicodedata.normalize('NFC', clean_text)
    
    return clean_text


def parse_xml_folder(folder_path):
    """
    Parse all XML files in the specified folder and extract attributes from w tags.
    
    Args:
        folder_path (str): Path to the folder containing XML files
        
    Returns:
        defaultdict: Dictionary with ref as key and tuples of (english, stronglemma, morph, text) as values
    """
    # Create a defaultdict to store the results
    results = defaultdict(list)
    
    # Loop through all files in the folder
    for filename in os.listdir(folder_path):
        if filename.endswith('.xml'):
            file_path = os.path.join(folder_path, filename)
            
            try:
                # Parse the XML file
                tree = ET.parse(file_path)
                root = tree.getroot()
                
                # Find all w tags in the XML
                for w_tag in root.findall('.//w'):
                    # Extract attributes (if they exist)
                    english = w_tag.get('english', '')
                    stronglemma = w_tag.get('stronglemma', '')
                    morph = w_tag.get('morph', '')
                    ref = w_tag.get('ref', '')
                    
                    # Get the text content of the w tag
                    text = w_tag.text or ''
                    
                    # Skip entries with no ref attribute (optional)
                    if not ref:
                        continue
                    
                    # Add the data to the defaultdict using ref as the key
                    results[ref].append((english, stronglemma, morph, text))
                    
            except Exception as e:
                print(f"Error processing {filename}: {e}")
    
    return results

def build_word(word):
    vowelless, full, lemma, gloss, morph = word
    return f'<span class="word-container" data-full="{full}" data-gloss="{gloss}" data-lemma="{lemma}" data-morph="{morph}"><span class="word">{vowelless}</span></span>'


def build_books(data):
    books = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    
    for ref, parts in data.items():
        book, rest = ref.split(' ', maxsplit=1)
        c, v  = rest.split(':', maxsplit=1)
        word =''
        lemma = ''
        gloss = ''
        morph = ''
        for (eng, lem, morph_code, text) in parts:
            word += text
            lemma += ' ' + lem
            morph += ' ' + morph_code
            gloss += ' ' + eng
        books[book][c][v.split('!')[0]].append((remove_hebrew_marks(word), word, lemma.strip().replace(' ', '+'), gloss.strip().replace(' ', '+'), morph.strip().replace(' ', '+')))

    return books



def sortem(xs):
    return sorted(xs, key=lambda x: int(x[0]))


BOOK_ORDER = [
    'GEN', 'EXO', 'LEV', 'NUM', 'DEU', 'JOS', 'JDG', 'RUT', '1SA', '2SA', '1KI', '2KI',
    '1CH', '2CH', 'EZR', 'NEH', 'EST', 'JOB', 'PSA', 'PRO', 'ECC', 'SNG', 'ISA', 'JER',
    'LAM', 'EZK', 'DAN', 'HOS', 'JOL', 'AMO', 'OBA', 'JON', 'MIC', 'NAM', 'HAB', 'ZEP',
    'HAG', 'ZEC', 'MAL',
]

# Static files in docs/ that the offline copy needs besides the generated pages.
PWA_STATIC_FILES = [
    'pwa.js',
    'manifest.webmanifest',
    'icons/icon-192.png',
    'icons/icon-512.png',
    'icons/icon-maskable-512.png',
    'icons/apple-touch-icon.png',
]


def book_key(book):
    return BOOK_ORDER.index(book) if book in BOOK_ORDER else len(BOOK_ORDER)


def render(body, home_link=True):
    return (TEMPLATE
            .replace('$homehidden$', '' if home_link else 'hidden')
            .replace('$body$', body))


def write_file_list(out_dir, page_names):
    """Write docs/files.json: everything the offline copy must contain, plus a
    version hash. The app compares this version with the one it downloaded to
    tell the user an update is available."""
    files = []
    digest = hashlib.sha256()
    for name in ['./', 'index.html'] + page_names + PWA_STATIC_FILES:
        path = out_dir / ('index.html' if name == './' else name)
        data = path.read_bytes()
        digest.update(name.encode() + b'\0' + data)
        files.append({'url': name, 'size': len(data)})
    listing = {'version': digest.hexdigest()[:16], 'files': files}
    (out_dir / 'files.json').write_text(json.dumps(listing, indent=1))


def build_output(data, out_dir=Path('docs')):
    index = {}
    for book, chapters in sorted(data.items(), key=lambda kv: book_key(kv[0])):
        bdata = []
        for chapter, verses in sortem(chapters.items()):
            cdata = []
            for verse, words in sortem(verses.items()):
                vdata = []

                for w in words:
                    vdata.append(build_word(w))
                cdata.append( f'<div><span class="vnum">{verse}</span>' + '\n'.join(vdata) + "</div>")
            bdata.append(f"<h1>{book} {chapter}</h1>" + '\n' + '\n'.join(cdata))
        name = f"Hebrew-reader-{book}.html"
        index[book] = name
        (out_dir / name).write_text(render(f"<h1>{book}</h1>" + '\n' + '\n'.join(bdata)), encoding='utf-8')
    (out_dir / "index.html").write_text(render(
        "<h1>Hebrew Bible reader without vowels</h1>" + '\n<div><ul>' + '\n'.join([
            f"<li><a href='{p}'>{book}</a></li>" for book, p in index.items()
        ]) + "</ul></div>", home_link=False), encoding='utf-8')
    write_file_list(out_dir, list(index.values()))


def main():
    # Specify the folder path (you should change this to your folder path)
    folder_path = Path(__file__).resolve().parent / "macula-hebrew-main" / "WLC" / "lowfat"
    # Parse the XML files
    result_dict = parse_xml_folder(folder_path)
    data = build_books(result_dict)
    build_output(data, Path(__file__).resolve().parent / 'docs')
    exit()
    # Print the results
    print("Results (organized by ref attribute):")
    for ref, values in result_dict.items():
        print(f"\nRef: {ref}")
        for i, (english, stronglemma, morph, text) in enumerate(values, 1):
            print(f"  Item {i}:")
            print(f"    English: {english}")
            print(f"    Strong Lemma: {stronglemma}")
            print(f"    Morph: {morph}")
            print(f"    Text: {text}")

if __name__ == "__main__":
    main()

