import streamlit as st
from pdf_utils import count_pdf_stats
from llm_summary import generate_summary

st.set_page_config(page_title='PDF Text Analyzer', page_icon='📄', layout='centered')
st.title('📄 PDF Text Analyzer')
st.caption('Extract text, view basic statistics, and generate a concise 3-line AI summary.')
uploaded = st.file_uploader('Upload a PDF', type=['pdf'])
if uploaded:
    try:
        with st.spinner('Extracting text...'):
            data = count_pdf_stats(uploaded)
    except Exception as exc:
        st.error(f'Could not read this PDF: {exc}')
        st.stop()
    c1, c2, c3 = st.columns(3)
    c1.metric('Words', f"{data['words']:,}")
    c2.metric('Characters', f"{data['characters']:,}")
    c3.metric('Pages', f"{data['pages']:,}")
    if not data['text'].strip():
        st.warning('No extractable text was found. This may be a scanned/image-only PDF.')
        st.stop()
    with st.expander('Preview extracted text'):
        st.text_area('Text', data['text'][:10000], height=300)
    if st.button('Generate 3-Line Summary', type='primary'):
        with st.spinner('Generating summary with Groq...'):
            try:
                st.markdown(generate_summary(data['text']))
            except Exception as exc:
                st.error(f'Could not generate the summary: {exc}')
else:
    st.info('Upload a PDF to begin.')
