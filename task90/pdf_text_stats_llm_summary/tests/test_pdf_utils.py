from pdf_utils import get_stats

def test_stats():
    r=get_stats('Hello world\nThis is a PDF.')
    assert r['words']==6 and r['characters']==26

def test_empty():
    r=get_stats('')
    assert r['words']==0 and r['characters']==0
