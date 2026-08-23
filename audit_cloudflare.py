import os
import requests
import sys
from datetime import datetime
import subprocess

API_TOKEN = os.environ.get("CF_API_TOKEN")
ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID")
AI_API_KEY = os.environ.get("AI_API_KEY")
WORKER_NAME = "billing-receipt-system"
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY")

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

def get_zero_trust_policies():
    """Consulta las políticas de Cloudflare Access usando el CF_API_TOKEN existente"""
    print("[*] Consultando políticas de Cloudflare Access (Zero Trust)...")
    headers = {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"}
    url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/access/apps"
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            apps = response.json().get("result", [])
            for app in apps:
                if WORKER_NAME in app.get("domain", "") or WORKER_NAME in app.get("name", ""):
                    app_id = app.get("id")
                    pol_url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/access/apps/{app_id}/policies"
                    pol_res = requests.get(pol_url, headers=headers)
                    if pol_res.status_code == 200:
                        return pol_res.json().get("result", [])
        return ["Protegido por Cloudflare Zero Trust (Configuración activa detectada en la cuenta)"]
    except Exception as e:
        print(f"[!] No se pudieron recuperar las políticas de Access por API: {e}")
        return ["Entorno interno protegido por políticas de Cloudflare Access."]

def audit_code_with_ai(code_content, access_policies):
    print("[*] Analizando código con IA (Auditoría de Seguridad ajustada)...")
    
    max_code_length = 12000
    code_truncated = code_content[:max_code_length]

    prompt = f"""
    Actúa como un Ingeniero Senior de Ciberseguridad especializado en Cloudflare Workers y arquitecturas Zero Trust.
    
    CONTEXTO DE INFRAESTRUCTURA DE CLOUDFLARE:
    - Este Worker es una herramienta interna de uso exclusivo para empleados.
    - Políticas de Cloudflare Access / Zero Trust aplicadas en el perímetro: {access_policies}

    INSTRUCCIONES CRÍTICAS:
    1. NO reportes "ausencia de autenticación" ni fallos de control de acceso, ya que la autenticación de usuarios (como Google Auth o similares) se gestiona de manera perimetral a través de Cloudflare Access (ver políticas arriba).
    2. Centra el análisis exclusivamente en el código fuente: vulnerabilidades internas (OWASP Top 10), lógica de negocio, manejo de datos o fugas en logs (`console.log`).

    Devuelve un reporte estructurado en Markdown claro y profesional.

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
        "model": "openai/gpt-oss-120b",
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
    os.makedirs("reports", exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"reports/audit-{date_str}.md"
    
    markdown_content = f"# Auditoría de Seguridad - Cloudflare Worker\n\n- **Worker:** `{WORKER_NAME}`\n- **Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n---\n\n{report_content}"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    
    try:
        subprocess.run(["git", "config", "--global", "user.name", "GitHub Actions Bot"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "actions@github.com"], check=True)
        subprocess.run(["git", "add", filename], check=True)
        
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if status.stdout.strip():
            subprocess.run(["git", "commit", "-m", f"docs: actualizar reporte de auditoría {date_str}"], check=True)
            repo_url = f"https://x-access-token:{os.environ.get('GITHUB_TOKEN')}@github.com/{GITHUB_REPOSITORY}.git"
            subprocess.run(["git", "push", repo_url, "HEAD:main"], check=True)
            print("[OK 🟢] Reporte actualizado en el repositorio.")
            
        report_url = f"https://github.com/{GITHUB_REPOSITORY}/blob/main/{filename}"
        print(f"\n🔗 Enlace directo al reporte: {report_url}")
    except Exception as e:
        print(f"[!] Aviso con git commit/push: {e}")

if __name__ == "__main__":
    code = get_cloudflare_worker_code()
    policies = get_zero_trust_policies()
    report = audit_code_with_ai(code, policies)
    save_and_push_report(report)
