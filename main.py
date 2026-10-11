"""PERSONA 5 - Punto de entrada.

    python main.py          -> abre la interfaz gráfica
    python main.py --demo   -> demo corta en consola (sin ventana)
"""
import sys

from emulador.transistor import Transistor
from emulador.gates import XOR, tabla_transistor_compuerta
from emulador.adders import SumadorN
from emulador.utils import entero_a_bits, bits_a_entero, bits_a_texto


def demo():
    print("== Tabla transistor -> compuerta (XOR) ==")
    for fila in tabla_transistor_compuerta(XOR()):
        print(fila)

    Transistor.reiniciar()
    sumador = SumadorN(8)
    a, b = 100, 55
    res, cout = sumador.sumar(entero_a_bits(a, 8), entero_a_bits(b, 8))
    print(f"\n{a} + {b} = {bits_a_entero(res)}  ({bits_a_texto(res)}), acarreo={cout}")
    print("Transistores emulados:", Transistor.total)


def main():
    if "--demo" in sys.argv:
        demo()
        return
    try:
        from ui import iniciar
    except ImportError as e:  # normalmente: Tkinter no instalado
        print("No se pudo abrir la interfaz:", e)
        print("Prueba 'python -m tkinter'. Mientras tanto: python main.py --demo")
        return
    iniciar()


if __name__ == "__main__":
    main()
