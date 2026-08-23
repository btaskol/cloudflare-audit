import os, requests, sys, smtplib, subprocess
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Credenciales y configuración
API_TOKEN = os.environ.get("CF_API_TOKEN")
ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID")
AI_API_KEY = os.environ.get("AI_API_KEY")
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
WORKER_NAME = "billing-receipt-system"
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY")

def get_cloudflare_worker_code():
    url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/workers/scripts/{WORKER_NAME}"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    res = requests.get(url, headers=headers)
    return res.text if res.status_code == 200 else sys.exit(1)

def get_zero_trust_policies():
    url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/access/apps"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    try:
        apps = requests.get(url, headers=headers).json().get("result", [])
        for app in apps:
            if WORKER_NAME in app.get("domain", ""):
                pol_url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/access/apps/{app.get('id')}/policies"
                return requests.get(pol_url, headers=headers).json().get("result", [])
        return ["Protegido por Cloudflare Zero Trust"]
    except:
        return ["Entorno interno protegido por Cloudflare Access."]

def audit_code_with_ai(code_content, access_policies):
    prompt = f"""
    Actúa como un Ingeniero de Ciberseguridad.
    INFRAESTRUCTURA: Worker interno protegido por Cloudflare Access: {access_policies}.
    NO reportes falta de autenticación general. Analiza el código fuente en busca de XSS, IDOR, inyecciones o fugas en logs.
    CÓDIGO: {code_content[:12000]}
    """
    payload = {"model": "openai/gpt-oss-120b", "messages": [{"role": "user", "content": prompt}], "temperature": 0.1}
    headers = {"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json"}
    res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
    return res.json()["choices"][0]["message"]["content"] if res.status_code == 200 else sys.exit(1)

def send_email_report(report_content):
    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = GMAIL_USER
    msg['Subject'] = f"Auditoría de Seguridad - {WORKER_NAME} - {datetime.now().strftime('%Y-%m-%d')}"
    msg.attach(MIMEText(report_content, 'plain'))
    
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("[OK] Email enviado correctamente.")
    except Exception as e:
        print(f"[!] Error enviando email: {e}")

if __name__ == "__main__":
    code = get_cloudflare_worker_code()
    policies = get_zero_trust_policies()
    report = audit_code_with_ai(code, policies)
    send_email_report(report)
