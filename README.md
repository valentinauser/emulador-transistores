# Emulador de transistores (CMOS) - Aritmética con IEEE 754

## Capas (cada una solo usa la de abajo)
Transistor -> Compuertas -> Sumadores -> Multiplicador/Divisor -> IEEE 754 -> Interfaz

| Archivo | Responsable | Contenido |
|---|---|---|
| emulador/transistor.py | Persona 2 | Transistor NMOS/PMOS + contador global |
| emulador/gates.py | Persona 2 | NOT, NAND, NOR, AND, OR, XOR, XNOR y tabla transistor->compuerta |
| emulador/adders.py | Persona 3 | Semisumador, sumador completo, sumador N bits, resta, flags |
| emulador/multiplier.py / divider.py | Persona 3 | Multiplicación y división |
| emulador/ieee754.py | Persona 4 | Codificar/decodificar y operaciones en float de 32 bits |
| main.py / UI / tests | Persona 5 | Integración, interfaz y pruebas |
| docs / presentación | Persona 1 | Investigación, diagramas, propuesta y diapositivas |

## Convención de bits
Lista de 0/1, índice 0 = bit menos significativo (LSB). Ver emulador/utils.py.

## Cómo correr
    python main.py
    pip install -r requirements.txt
    pytest
