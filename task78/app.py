import streamlit as st
from chatbot.llm_service import extract_conversion
from chatbot.parser import ParseError
from conversion.converter import ConversionError, convert_unit, get_unit_label

st.set_page_config(page_title="Unit Conversion Chatbot", page_icon="🔄", layout="centered")
st.title("🔄 Unit Conversion Chatbot")
st.caption("Ask in English or Urdu/Hinglish. The AI reads the request; Python does every calculation.")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hi! Try: **5 km ko miles mein convert karo**."}]
for message in st.session_state.messages:
    with st.chat_message(message["role"]): st.markdown(message["content"])

with st.expander("Example questions"):
    st.markdown("- Convert 10 kilograms to pounds\n- How many meters are in 3 kilometers?\n- 25 Celsius ko Fahrenheit mein convert karo\n- Convert 2.5 liters to gallons")

if prompt := st.chat_input("Type a conversion question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Understanding your request..."):
            try:
                request, source = extract_conversion(prompt)
                result = convert_unit(request.value, request.from_unit, request.to_unit)
                answer = (f"{request.value:g} {get_unit_label(request.from_unit, request.value)} = "
                          f"**{result:.6g} {get_unit_label(request.to_unit, result)}**")
                if source == "local parser": answer += "\n\n*Running with the local parser—add `GROQ_API_KEY` to `.env` to enable LLM extraction.*"
            except (ParseError, ConversionError) as exc:
                answer = f"⚠️ {exc}"
            except Exception:
                answer = "⚠️ Something unexpected went wrong. Please try again."
            st.markdown(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})
