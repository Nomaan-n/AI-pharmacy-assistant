import os, smtplib
from email.message import EmailMessage

def send_email(to:str, subject:str, body:str):
    host=os.getenv('SMTP_HOST'); sender=os.getenv('SMTP_FROM') or os.getenv('SMTP_USER')
    if not host or not sender: return False
    msg=EmailMessage(); msg['From']=sender; msg['To']=to; msg['Subject']=subject; msg.set_content(body)
    with smtplib.SMTP(host,int(os.getenv('SMTP_PORT','587')),timeout=10) as smtp:
        if os.getenv('SMTP_TLS','true').lower()=='true': smtp.starttls()
        user=os.getenv('SMTP_USER'); password=os.getenv('SMTP_PASSWORD')
        if user and password: smtp.login(user,password)
        smtp.send_message(msg)
    return True

def send_welcome_email(to:str):
    return send_email(to,'Welcome to PharmaPal','Welcome to PharmaPal. We made medicine search, scanning, verification, your private medicine cabinet and reminders easier to access in one place.\n\nYou can use PharmaPal to research medication information and organize your medicines. For personal medical decisions, prescriptions, doses and emergencies, use a qualified doctor or pharmacist.\n\nNeed human help? PharmaPal can offer an optional paid review request where an appropriately qualified professional can review the information you provide. This is not a diagnosis, prescription, emergency service or guarantee of a particular medicine or doctor.')
