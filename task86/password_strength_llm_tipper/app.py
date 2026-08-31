import streamlit as st
from strength_checker import check_password_strength
from llm_tip import generate_personalized_tip

st.set_page_config(page_title='Password Strength Checker', page_icon='🔐')
st.title('🔐 Password Strength Checker')
st.caption('Local deterministic checks + Groq personalized security tip')
st.info('Your password is checked locally and is never sent to the LLM. Only aggregate strength results are used for the tip.')
password = st.text_input('Enter a password to check', type='password')
if password:
    result = check_password_strength(password)
    st.subheader('Strength')
    st.progress(result['score']/100)
    if result['score'] >= 80: st.success(f"🟢 {result['label']} — {result['score']}/100")
    elif result['score'] >= 50: st.warning(f"🟡 {result['label']} — {result['score']}/100")
    else: st.error(f"🔴 {result['label']} — {result['score']}/100")
    cols=st.columns(4)
    for col,(name,ok) in zip(cols,[('Length',result['checks']['length']),('Uppercase',result['checks']['uppercase']),('Number',result['checks']['number']),('Symbol',result['checks']['symbol'])]): col.metric(name,'✓' if ok else '✗')
    st.subheader('Analysis')
    for m in result['messages']: st.write(('✅ ' if m['passed'] else '❌ ')+m['text'])
    st.subheader('🤖 Personalized Tip')
    with st.spinner('Generating tip...'):
        try: st.write(generate_personalized_tip(result))
        except Exception: st.warning('LLM tip unavailable. Check your Groq API configuration.')
else:
    st.markdown('### Rules checked')
    st.write('- Minimum 8 characters\n- At least one uppercase letter\n- At least one number\n- At least one symbol\n- Longer passwords receive a higher score')
