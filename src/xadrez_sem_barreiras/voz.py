import platform
import shutil
import subprocess
import threading


class LeitorVoz:
    """
    Faz o computador falar sem travar a câmera.

    Windows: usa a voz nativa do sistema via PowerShell/System.Speech.
    Linux: tenta spd-say ou espeak, se algum estiver instalado.
    macOS: tenta o comando say.

    velocidade: 1.0 (normal) até 4.0 (muito rápido). Padrão 1.0.
    """

    def __init__(self, ativo=True, velocidade=1.0):
        self.ativo = ativo
        self.velocidade = max(1.0, min(4.0, velocidade))
        self._lock = threading.Lock()

    def alternar(self):
        self.ativo = not self.ativo
        return self.ativo

    def falar(self, texto):
        if not texto:
            return

        print(f"[voz] {texto}")

        if not self.ativo:
            return

        thread = threading.Thread(target=self._falar_bloqueante, args=(texto,), daemon=True)
        thread.start()

    def _falar_bloqueante(self, texto):
        with self._lock:
            sistema = platform.system().lower()

            try:
                if "windows" in sistema:
                    self._falar_windows(texto)
                    return

                if "darwin" in sistema and shutil.which("say"):
                    wpm = int(175 * self.velocidade)
                    subprocess.run(["say", "-r", str(wpm), texto],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return

                if shutil.which("spd-say"):
                    rate = int(50 + (self.velocidade - 1.0) * (50.0 / 3.0))
                    subprocess.run(["spd-say", "-l", "pt-BR", "-r", str(rate), texto],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return

                if shutil.which("espeak") or shutil.which("espeak-ng"):
                    wpm = min(int(150 * self.velocidade), 500)
                    cmd = "espeak-ng" if shutil.which("espeak-ng") else "espeak"
                    subprocess.run([cmd, "-v", "pt-br", "-s", str(wpm), texto],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return

                print("[voz] Nenhum sintetizador de voz encontrado neste sistema.")
            except Exception as erro:
                print(f"[voz] Não foi possível falar: {erro}")

    def _falar_windows(self, texto):
        texto_seguro = texto.replace("'", "''")
        rate = int((self.velocidade - 1.0) * (10.0 / 3.0))
        comando = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$s.Volume = 100; "
            f"$s.Rate = {rate}; "
            f"$s.Speak('{texto_seguro}');"
        )

        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", comando],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
