import os
import requests
import sys

# 1. Cambiamos ZONE_ID por ACCOUNT_ID
API_TOKEN = os.environ.get("CF_API_TOKEN")
ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID")
WORKER_NAME = "billing-receipt-system"

if not API_TOKEN or not ACCOUNT_ID:
    print("[!] Error: Faltan las credenciales CF_API_TOKEN o CF_ACCOUNT_ID en los secrets.")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

def audit_worker_code():
    """Descarga el código actual del Worker desde Cloudflare para analizarlo."""
    url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/workers/scripts/{WORKER_NAME}"
    
    print(f"[*] Descargando código del Worker: {WORKER_NAME}...")
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code == 200:
        code_content = response.text
        print("[OK 🟢] Código del Worker descargado correctamente.")
        
        # --- AQUÍ APLICAS TUS COMPROBACIONES O INTEGRACIÓN CON CLAUDE ---
        # Ejemplo básico de validación estática local:
        if "eval(" in code_content:
            print("[ALERTA 🔴] Se detectó el uso inseguro de 'eval()' en el código.")
            return False
            
        if "console.log" in code_content:
            print("[AVISO 🟡] Hay llamadas a 'console.log', asegúrate de no filtrar datos sensibles.")
            
        return True
    else:
        print(f"[!] Error al obtener el Worker de la API ({response.status_code}): {response.text}")
        return False

if __name__ == "__main__":
    print(f"Iniciando auditoría para la cuenta: {ACCOUNT_ID}\n")
    
    code_secure = audit_worker_code()
    
    if not code_secure:
        print("\n[!] La auditoría del Worker ha fallado.")
        sys.exit(1)
    else:
        print("\n[ÉXITO] Auditoría del Worker completada sin problemas críticos.")
        sys.exit(0)
