# HR Streamlit UI patch

## Install

Back up the current application first:

```powershell
Copy-Item app.py app_before_new_ui.py
```

Copy all files from this patch into the project root and install:

```powershell
pip install streamlit-aggrid openpyxl pyarrow
streamlit run app.py
```

## What changed in this revision

- The screenshot-derived purple AI Chatbot pill was removed.
- The top header is now built from the supplied Synvert ClearPeaks SVG logo.
- The logo is shown at its natural aspect ratio without cropping.
- Report cards now have two actions:
  - **Open**: opens in the current tab.
  - **New tab**: opens an independent Streamlit session in a new browser tab.
- Multiple reports can therefore remain open at the same time.
- Reports are resolved through the URL query parameter `report_key`, so a new tab does not depend on the original tab's session state.
- Parquet files and report business logic are unchanged.
