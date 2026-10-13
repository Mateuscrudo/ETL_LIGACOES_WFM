import time

TEMPOS = {}

def cronometro(nome,inicio):
    tempo = time.time()-inicio
    TEMPOS[nome]=tempo
    print(f"⏱ {nome:<20}: {tempo:.2f}s")