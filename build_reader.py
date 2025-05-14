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
    <title>Word with Hidden Data</title>
    <style>
        .word-container {
            display: inline-block;
            position: relative;
            margin: 10px;
            cursor: pointer;
        }
        
        .word {
            font-weight: normal;
            color: #2c3e50;
            border-bottom: 1px dashed #3498db;
            padding: 2px 4px;
            font-size: 1.15em;
        }
        
        .data {
            position: absolute;
            top: 100%;
            left: 0;
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            padding: 8px;
            margin-top: 5px;
            min-width: 150px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            display: none;
            z-index: 100;
            font-size: 1.25empx;

            color: #333;
        }
        
        .word-container:hover .data,
        .word-container.show-data .data {
            display: block;
        }
        
        /* Example styling for multiple instances */
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0 auto;
            max-width: 700px;
            padding: 20px;
        }
        
        .paragraph {
            max-width: 600px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
$body$
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Get all word containers
            const wordContainers = document.querySelectorAll('.word-container');
            
            // Helper function to hide data after delay
            function hideDataAfterDelay(container) {
                setTimeout(() => {
                    container.classList.remove('show-data');
                }, 3000);
            }
            
            // For each word container, attach event listeners
            wordContainers.forEach(container => {
                let timeout;
                
                // For both desktop (mouseenter) and mobile (click) interactions
                
                // Mouse enter - for desktop
                container.addEventListener('mouseenter', function() {
                    // Clear any existing timeout
                    clearTimeout(timeout);
                });
                
                // Mouse leave - for desktop
                container.addEventListener('mouseleave', function() {
                    timeout = setTimeout(() => {
                        container.classList.remove('show-data');
                    }, 3000);
                });
                
                // Click/tap - for mobile and desktop
                container.addEventListener('click', function(e) {
                    // Prevent any parent click events
                    e.stopPropagation();
                    
                    // Add class to show data
                    container.classList.add('show-data');
                    
                    // Clear any existing timeout
                    clearTimeout(timeout);
                    
                    // Set timeout to hide data after 3 seconds
                    hideDataAfterDelay(container);
                });
            });
            
            // Hide any shown data when clicking elsewhere
            document.addEventListener('click', function() {
                wordContainers.forEach(container => {
                    container.classList.remove('show-data');
                });
            });
        });
    </script>
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
    return f"""
    <div class="word-container">
        <span class="word">{vowelless}</span>
        <div class="data"><p>{full}</p><p>{gloss}</p><p>{lemma}</p><p>{morph}</p></div>
    </div>
        
    """


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


def build_output(data):
    index = {}
    for book, chapters in data.items():
        bdata = []
        for chapter, verses in sortem(chapters.items()):
            cdata = []
            print(verses)
            for verse, words in sortem(verses.items()):
                vdata = []

                for w in words:
                    vdata.append(build_word(w))
                cdata.append( f'<div><span class="vnum">{verse}</span>' + '\n'.join(vdata) + "</div>")
            bdata.append(f"<h1>{book} {chapter}</h1>" + '\n' + '\n'.join(cdata))
        name = f"Hebrew-reader-{book}.html"
        index[book] = name
        Path('docs/' + name).write_text(TEMPLATE.replace('$body$', f"<h1>{book}</h1>" + '\n' + '\n'.join(bdata)))
    Path("docs/index.html").write_text(TEMPLATE.replace('$body$',
                                                   "<h1>Hebrew Bible reader without vowels</h1>" + '\n<div><ul>' +  '\n'.join([
        f"<li><a href='{p}'>{book}</a></li>" for book, p in index.items()                                                                                                                     
    ]) + "</ul></div>"))
                
            
            
            
        

def main():
    # Specify the folder path (you should change this to your folder path)
    folder_path = "/Users/fhardison/Documents/_Projects/hebrew-no-vowels-reader/macula-hebrew-main/WLC/lowfat"
    # Parse the XML files
    result_dict = parse_xml_folder(folder_path)
    data = build_books(result_dict)
    build_output(data)
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

