from colorama import Fore, Style, init

init(autoreset=True)

def titulo(texto):
    print("\n" + "="*50)
    print(texto)
    print("="*50)

def sucesso(texto):
    print(Fore.GREEN + "✅ " + texto)

def aviso(texto):
    print(Fore.YELLOW + "⚠ " + texto)

def erro(texto):
    print(Fore.RED + "❌ " + texto)

def info(texto):
    print(Fore.CYAN + "ℹ " + texto)