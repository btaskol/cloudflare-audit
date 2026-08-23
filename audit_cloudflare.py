import os
import requests
import sys

# Obtener variables de entorno inyectadas por GitHub Actions
API_TOKEN = os.environ.get("CF_API_TOKEN")
ZONE_ID = os.environ.get("CF_ZONE_ID")

if not API_TOKEN or not ZONE_ID:
    print("[!] Error: Faltan las credenciales CF_API_TOKEN o CF_ZONE_ID.")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

def check_tls_version():
    url = f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/settings/min_tls_version"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code == 200:
        tls_value = response.json()['result']['value']
        if tls_value not in ["1.2", "1.3"]:
            print(f"[ALERTA 🔴] Versión TLS mínima insegura detectada: {tls_value}. Debería ser 1.2 o 1.3")
            return False
        else:
            print(f"[OK 🟢] Versión TLS correcta: {tls_value}")
            return True
    return False

def check_waf_rules():
    # Aquí puedes añadir la lógica para verificar si las reglas gestionadas están en modo 'block'
    print("[INFO 🔵] Verificando reglas de WAF (Pendiente de implementar)...")
    return True

if __name__ == "__main__":
    print(f"Iniciando auditoría CSPM para la zona: {ZONE_ID}\n")
    
    tls_secure = check_tls_version()
    waf_secure = check_waf_rules()
    
    # Además de auditar la seguridad, este mismo flujo puede consultar la API GraphQL 
    # de Cloudflare para monitorizar tus reglas de caché. Extraer estos datos a diario es ideal 
    # para recopilar la evidencia necesaria que demuestre de forma continuada cómo el uso 
    # del caching está absorbiendo el tráfico y ahorrando costes en la infraestructura.
    
    if not tls_secure or not waf_secure:
        print("\n[!] La auditoría ha fallado. Revisa las alertas arriba.")
        sys.exit(1) # Esto hace que el pipeline de GitHub Actions marque un error (cruz roja)
    else:
        print("\n[ÉXITO] Auditoría completada sin fallos críticos de configuración.")
        sys.exit(0)
