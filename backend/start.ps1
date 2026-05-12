$python = "D:\python_project\kubemind\.venv\Scripts\python.exe"
& $python -m uvicorn app.main:app --host 127.0.0.1 --port 10000 --reload
