import fitz

def count_pdf_stats(uploaded_file):
    data = uploaded_file.getvalue()
    if not data:
        raise ValueError('The uploaded PDF is empty.')
    document = fitz.open(stream=data, filetype='pdf')
    try:
        text = '\n'.join(page.get_text('text') for page in document).strip()
        return {'text': text, 'words': len(text.split()), 'characters': len(text), 'pages': len(document)}
    finally:
        document.close()

def get_stats(text):
    if not isinstance(text, str):
        raise TypeError('text must be a string')
    return {'words': len(text.split()), 'characters': len(text), 'pages': 0}
