import os
import requests
import sys
from datetime import datetime
import subprocess

API_TOKEN = os.environ.get("CF_API_TOKEN")
ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID")
AI_API_KEY = os.environ.get("AI_API_KEY")
WORKER_NAME = "billing-receipt-system"
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY") # Proporcionado automáticamente por GitHub Actions

if not API_TOKEN or not ACCOUNT_ID or not AI_API_KEY:
    print("[!] Error: Faltan credenciales necesarias en los secrets.")
    sys.exit(1)

def get_cloudflare_worker_code():
    url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/workers/scripts/{WORKER_NAME}"
    headers = {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"}
    
    print(f"[*] Descargando código del Worker: {WORKER_NAME}...")
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.text
    else:
        print(f"[!] Error al obtener el Worker ({response.status_code}): {response.text}")
        sys.exit(1)

def audit_code_with_ai(code_content):
    print("[*] Analizando código con IA (Auditoría de Seguridad)...")
    
    # Trunca el contenido del worker usando el nombre correcto del parámetro
    max_code_length = 12000
    code_truncated = code_content[:max_code_length]

    prompt = f"""
    Actúa como un Ingeniero Senior de Ciberseguridad especializado en Cloudflare Workers.
    IMPORTANTE: Este Cloudflare Worker es una aplicación interna de uso exclusivo para EMPLEADOS de la empresa (no es una plataforma pública para clientes). 
    
    Analiza el siguiente código fuente en busca de:
    1. Vulnerabilidades de seguridad (OWASP Top 10, control de acceso interno, fugas de datos).
    2. Exposición accidental de secretos, API keys o datos sensibles en logs (`console.log`).
    3. Validación correcta de que las peticiones provienen de la red interna o empleados autorizados.

    Devuelve un reporte estructurado y claro indicando riesgos críticos (ALTO, MEDIO, BAJO) y sugerencias de corrección en formato Markdown.

    CÓDIGO DEL WORKER:
    ```javascript
    {code_truncated}
    ```
    """
    ai_url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "openai/gpt-oss-120b",  # 👈 Modelo activo y recomendado para análisis de código
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }

    res = requests.post(ai_url, json=payload, headers=headers)
    if res.status_code == 200:
        return res.json()["choices"][0]["message"]["content"]
    else:
        print(f"[!] Error al contactar con la API de IA: {res.text}")
        sys.exit(1)

def save_and_push_report(report_content):
    # Crear carpeta reports si no existe
    os.makedirs("reports", exist_ok=True)
    
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"reports/audit-{date_str}.md"
    
    # Escribir el reporte en formato Markdown
    markdown_content = f"# Auditoría de Seguridad - Cloudflare Worker\n\n- **Worker:** `{WORKER_NAME}`\n- **Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n---\n\n{report_content}"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    
    print(f"[OK 🟢] Reporte guardado localmente en {filename}")
    
    # Configurar git e intentar subir el reporte automáticamente al repo
    try:
        subprocess.run(["git", "config", "--global", "user.name", "GitHub Actions Bot"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "actions@github.com"], check=True)
        subprocess.run(["git", "add", filename], check=True)
        
        # Verificar si hay cambios para commitear
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if status.stdout.strip():
            subprocess.run(["git", "commit", "-m", f"docs: añadir reporte de auditoría de {date_str}"], check=True)
            # Push usando el token por defecto de GitHub Actions
            repo_url = f"https://x-access-token:{os.environ.get('GITHUB_TOKEN')}@github.com/{GITHUB_REPOSITORY}.git"
            subprocess.run(["git", "push", repo_url, "HEAD:main"], check=True)
            print("[OK 🟢] Reporte subido al repositorio correctamente.")
        else:
            print("[*] No hay cambios nuevos en el reporte.")
            
        report_url = f"https://github.com/{GITHUB_REPOSITORY}/blob/main/{filename}"
        print(f"\n🔗 Enlace directo al reporte: {report_url}")
        
    except Exception as e:
        print(f"[!] Aviso al intentar hacer commit automático: {e}")

if __name__ == "__main__":
    code = get_cloudflare_worker_code()
    report = audit_code_with_ai(code)
    save_and_push_report(report)
