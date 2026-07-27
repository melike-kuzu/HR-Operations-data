import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from chatbot import ask_data_question

questions = [
    "List consultants available on 2026-12-01.",
    "List consultants with advanced AWS skills.",
    "List consultants available on 2026-12-01 with advanced AWS skills.",
    "List consultants with banking experience.",
    "List consultants available on 2026-12-01 with advanced AWS skills and banking experience.",
]

for question in questions:
    print("\nQUESTION:", question, flush=True)

    result = ask_data_question(question)

    print("ANSWER:", flush=True)
    print(result["answer"], flush=True)

    for name, df in result["tables"].items():
        print("\nTABLE:", name, df.shape, flush=True)
        print(df.head(), flush=True)