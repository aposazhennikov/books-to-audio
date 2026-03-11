from pathlib import Path
from book_normalizer.loaders.fb2_loader import Fb2Loader

# Load FB2.
path = Path('books/monosov2.fb2')
loader = Fb2Loader()
book = loader.load(path)

print(f'Chapters: {len(book.chapters)}')
print()

# Show first 30 paragraphs.
all_paras = []
for chapter in book.chapters:
    all_paras.extend(chapter.paragraphs)

print(f'Total paragraphs: {len(all_paras)}')
print()
print('First 30 paragraph first lines:')
for i, para in enumerate(all_paras[:30]):
    first_line = para.raw_text.strip().split('\n')[0][:80]
    print(f'{i}: "{first_line}"')
