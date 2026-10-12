"""
LANZADOR MASTER SUITE UNIFICADA (Challenger Automotive 4-in-1)
==============================================================
Inicia el servidor Flask + Cron Sync Engine en segundo plano y abre la Web App
directamente en tu navegador predeterminado en el puerto 5050.

Uso: python run_suite.py
"""

import webbrowser
import threading
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app

def abrir_navegador():
    time.sleep(1.5)
    url = "http://127.0.0.1:5050"
    print(f"\nAbriendo Challenger Master Suite en tu navegador: {url}\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass

if __name__ == "__main__":
    threading.Thread(target=abrir_navegador, daemon=True).start()
    print("==========================================================")
    print("CHALLENGER AUTOMOTIVE - MASTER SUITE ERP UNIFICADA 4-IN-1")
    print("==========================================================")
    print("Modulos: Stock | Top Productos | Comisiones | SAT Pasivos")
    print("Servidor activo en: http://127.0.0.1:5050 (y en red local http://192.168.1.119:5050)")
    print("Presiona Ctrl+C para detener el servidor.\n")
    app.run(host="0.0.0.0", port=5050, debug=False, threaded=True)
