import streamlit as st


st.set_page_config(
    page_title="HR Operations Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


dashboard_page = st.Page(
    "pages/dashboard.py",
    title="Dashboard",
    icon=":material/dashboard:",
    default=True,
)

reports_page = st.Page(
    "pages/reports.py",
    title="Reports",
    icon=":material/table_view:",
)

chatbot_page = st.Page(
    "pages/chatbot_page.py",
    title="HR Assistant",
    icon=":material/smart_toy:",
)


navigation = st.navigation(
    {
        "Overview": [dashboard_page],
        "HR Operations": [reports_page],
        "AI": [chatbot_page],
    }
)

navigation.run()