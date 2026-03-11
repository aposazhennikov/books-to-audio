from pathlib import Path
from book_normalizer.loaders.fb2_loader import Fb2Loader

# Load FB2.
path = Path('books/monosov2.fb2')
loader = Fb2Loader()
book = loader.load(path)

all_paras = []
for chapter in book.chapters:
    all_paras.extend(chapter.paragraphs)

print('Paragraphs 4, 28, 29:')
for i in [4, 28, 29]:
    para = all_paras[i]
    print(f'\nParagraph {i}:')
    print(f'Text: {repr(para.raw_text[:200])}')
    print(f'Length: {len(para.raw_text)}')
