import os
import sys
import webbrowser
from threading import Timer
import streamlit.web.cli as stcli

def open_browser():
    webbrowser.open("http://localhost:8501")

if __name__ == "__main__":
    if getattr(sys, 'frozen', False):
        # When contents_directory='libs' is used in the SPEC file, 
        # sys._MEIPASS points to the internal 'libs' folder.
        libs_dir = sys._MEIPASS
        root_dir = os.path.dirname(libs_dir)
        
        # Add libs to sys.path for the current process
        if libs_dir not in sys.path:
            sys.path.insert(0, libs_dir)
        
        # Ensure sub-processes (like streamlit workers) can find the libs
        os.environ["PYTHONPATH"] = libs_dir + os.pathsep + os.environ.get("PYTHONPATH", "")
        
        os.chdir(root_dir)
        script_path = os.path.join(libs_dir, "core", "workbench_main.py")
    else:
        script_path = "core/workbench_main.py"

    print(f"Launching from: {script_path}")
    
    sys.argv = [
        "streamlit", 
        "run", 
        script_path, 
        "--global.developmentMode=false", 
        "--logger.level=error",
        "--client.toolbarMode=viewer",
        "--browser.gatherUsageStats=false",
        "--server.headless=true",
        "--server.address=localhost",
        "--server.showEmailPrompt=false",
        "--server.enableCORS=false",
        "--server.enableXsrfProtection=false",
        "--theme.primaryColor=#005FB8",
        "--theme.backgroundColor=#FFFFFF",
        "--theme.secondaryBackgroundColor=#F0F2F6",
        "--theme.textColor=#262730",
        "--theme.font=inter"
    ]        
    
    Timer(1.5, open_browser).start()
    sys.exit(stcli.main())
