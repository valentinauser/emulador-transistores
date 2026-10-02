"""PERSONA 5 - Punto de entrada / demo. Aquí se integra todo (luego la UI)."""
from emulador.transistor import Transistor
from emulador.gates import NAND, XOR, tabla_transistor_compuerta
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


if __name__ == "__main__":
    demo()
