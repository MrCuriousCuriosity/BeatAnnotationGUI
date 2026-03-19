#!/bin/bash 

# This makes the GUI auto-restart when I save a file. 
# needs:    pip install watchdog && chmod +x run_with_watch.sh
# run with: ./run_with_watch.sh 

# Explicação (tirar isto depois)
# auto-restart: watches for changes in .py files in the current directory and subdirectories
# patterns: only watch .py files
# recursive: watch subdirectories
# debounce: wait 1 seconds after a change before restarting. 
    # Avoids multiple restarts if multiple files are changed at once 
    # A ideia é evitar que ele compile quando o codigo ta incompleto. Mas ainda n testei se funciona.

watchmedo auto-restart --patterns="*.py" --recursive --debounce=1 -- python 000_main_BA_GUI.py