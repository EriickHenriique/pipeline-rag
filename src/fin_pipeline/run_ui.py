import subprocess
import sys

if __name__ == "__main__":
    subprocess.run(
        [
            sys.executable, "-m", "streamlit", "run",
            "src/fin_pipeline/ui/streamlit_app.py",
            "--server.port", "8501",
            "--server.address", "localhost",
        ]
    )