"""PERSONA 5 - Controlador: une la interfaz con las capas del emulador.

Aquí NO hay ventanas (eso está en ui.py). Todo lo que la interfaz necesita
mostrar se calcula en este archivo, así se puede probar sin abrir Tkinter.

Regla del equipo: las operaciones se hacen SOLO con el emulador (transistores).
Este archivo usa 'struct' únicamente para convertir lo que escribe el usuario
(decimal) a bits y para mostrar el resultado (bits -> decimal), igual que un
monitor convierte voltajes en pixeles. Los operadores + - * / de Python se usan
solo en 'esperado_nativo', que sirve para COMPROBAR el resultado.
"""
import math
import struct
import time
from contextlib import contextmanager
from dataclasses import dataclass, field

from emulador import ieee754
from emulador.adders import SumadorCompleto
from emulador.gates import (Compuerta, NOT, NAND, NOR, AND, OR, XOR, XNOR,
                            tabla_transistor_compuerta)
from emulador.transistor import Transistor
from emulador.utils import entero_a_bits, bits_a_entero, bits_a_texto

# Símbolo de la operación -> (nombre, función del emulador)
OPERACIONES = {
    "+": ("Suma", ieee754.float_add),
    "-": ("Resta", ieee754.float_sub),
    "×": ("Multiplicación", ieee754.float_mul),
    "÷": ("División", ieee754.float_div),
}

# Nombres amigables de las piezas de hardware de la unidad IEEE 754
ETIQUETAS_HARDWARE = {
    "mult": "Multiplicador 24x24",
    "div": "Divisor 50 bits",
    "sum_exp": "Sumador exponentes (10 b)",
    "sum24": "Sumador redondeo (24 b)",
    "sum27": "Sumador mantisas (27 b)",
    "comp_exp": "Comparador exponentes",
    "comp_man": "Comparador mantisas",
    "xor": "XOR (signos)",
    "and_": "AND",
    "or_": "OR (sticky)",
    "not_": "NOT (invertir signo)",
}


# ---------------------------------------------------------------------------
# Conversión de entrada / salida (decimal <-> 32 bits)
# ---------------------------------------------------------------------------

def leer_numero(texto):
    """Convierte el texto del usuario en float. Acepta coma decimal, inf y nan."""
    limpio = texto.strip().replace(",", ".")
    if not limpio:
        raise ValueError("Falta escribir un número.")
    try:
        return float(limpio)
    except ValueError:
        raise ValueError(f"'{texto.strip()}' no es un número válido.")


def float_a_bits(x):
    """Decimal -> lista de 32 bits (LSB primero), redondeado a float32."""
    try:
        n = struct.unpack(">I", struct.pack(">f", x))[0]
    except OverflowError:  # demasiado grande para float32 -> infinito
        n = 0x7F800000 | (0x80000000 if x < 0 else 0)
    return entero_a_bits(n, 32)


def bits_a_float(bits):
    """Lista de 32 bits (LSB primero) -> decimal."""
    return struct.unpack(">f", struct.pack(">I", bits_a_entero(bits)))[0]


def texto_valor(x):
    if math.isnan(x):
        return "NaN"
    if math.isinf(x):
        return "inf" if x > 0 else "-inf"
    return format(x, ".9g")


def campos(bits32):
    """Separa los 32 bits en signo | exponente | mantisa para mostrarlos."""
    signo, exp, mant, tipo = ieee754.decodificar(bits32)
    e = bits_a_entero(exp)
    if tipo == ieee754.TIPO_NORMAL:
        real = e - ieee754.SESGO
    elif tipo == ieee754.TIPO_DESNORMALIZADO:
        real = 1 - ieee754.SESGO
    else:
        real = None
    return {
        "signo": str(signo),
        "exp": bits_a_texto(exp),
        "mant": bits_a_texto(mant),
        "exp_valor": e,
        "exp_real": real,
        "tipo": tipo,
        "hex": f"0x{bits_a_entero(bits32):08X}",
        "valor": bits_a_float(bits32),
    }


# ---------------------------------------------------------------------------
# Verificación contra Python (SOLO para comprobar, nunca para calcular)
# ---------------------------------------------------------------------------

def esperado_nativo(a, b, simbolo):
    try:
        if simbolo == "+":
            r = a + b
        elif simbolo == "-":
            r = a - b
        elif simbolo == "×":
            r = a * b
        else:
            r = a / b
    except ZeroDivisionError:  # Python lanza error; IEEE 754 da inf o NaN
        if a == 0 or math.isnan(a):
            r = math.nan
        else:
            r = math.copysign(math.inf, a) * math.copysign(1.0, b)
    return float_a_bits(r)


def mismos_bits(x32, y32):
    """Igualdad bit a bit; cualquier NaN cuenta como igual a cualquier NaN."""
    if (ieee754.decodificar(x32)[3] == ieee754.TIPO_NAN
            and ieee754.decodificar(y32)[3] == ieee754.TIPO_NAN):
        return True
    return list(x32) == list(y32)


# ---------------------------------------------------------------------------
# Medición de actividad de transistores
# ---------------------------------------------------------------------------

class Telemetria:
    def __init__(self):
        self.evaluados = set()   # transistores que recibieron una señal
        self.conducen = set()    # transistores que conducieron al menos una vez
        self.evaluaciones = 0    # total de veces que se evaluó un transistor


@contextmanager
def medir():
    """Mientras dura el 'with', anota qué transistores se usan.
    No modifica el emulador: envuelve Transistor.conduce y luego lo restaura."""
    tele = Telemetria()
    original = Transistor.conduce

    def espia(self, gate):
        estado = original(self, gate)
        tele.evaluaciones += 1
        tele.evaluados.add(id(self))
        if estado:
            tele.conducen.add(id(self))
        return estado

    Transistor.conduce = espia
    try:
        yield tele
    finally:
        Transistor.conduce = original


def componentes(unidad):
    """Piezas de hardware (compuertas/sumadores/etc.) de la unidad IEEE 754."""
    return [(n, o) for n, o in vars(unidad).items() if isinstance(o, Compuerta)]


def actividad(unidad, tele):
    """Filas (componente, transistores, usados, conducen) de la última operación."""
    filas = []
    for nombre, comp in componentes(unidad):
        ts = comp.todos_los_transistores()
        usados = sum(1 for t in ts if id(t) in tele.evaluados)
        cond = sum(1 for t in ts if id(t) in tele.conducen)
        filas.append((ETIQUETAS_HARDWARE.get(nombre, nombre), len(ts), usados, cond))
    return filas


# Para la interfaz: 4 grupos fáciles de explicar en vez de 11 componentes
GRUPOS_HARDWARE = [
    ("Sumadores y comparadores", ("Sumador", "Comparador")),
    ("Multiplicador", ("Multiplicador",)),
    ("Divisor", ("Divisor",)),
    ("Signos y redondeo", ("XOR", "AND", "OR", "NOT")),
]


def agrupar_actividad(filas):
    """Junta las filas de 'actividad' en GRUPOS_HARDWARE.
    Devuelve [(grupo, transistores, usados)]."""
    acum = {nombre: [0, 0] for nombre, _ in GRUPOS_HARDWARE}
    for etiqueta, total, usados, _cond in filas:
        for nombre, prefijos in GRUPOS_HARDWARE:
            if etiqueta.startswith(prefijos):
                acum[nombre][0] += total
                acum[nombre][1] += usados
                break
    return [(n, acum[n][0], acum[n][1]) for n, _ in GRUPOS_HARDWARE]


# Compuertas que se muestran en la interfaz: 3 primitivas (transistores
# directos) y 3 compuestas (hechas con las anteriores).
COMPUERTAS_MOSTRADAS = ("NOT", "NAND", "NOR", "AND", "OR", "XOR")
_ESTRUCTURA = None  # (unidad, [(nombre, [ids de sus transistores])]) en caché


def _recolectar(comp, salida):
    """Anota cada compuerta con los ids de TODOS sus transistores."""
    ids = [id(t) for t in comp.transistores]
    for parte in comp.partes:
        ids += _recolectar(parte, salida)
    if comp.nombre in COMPUERTAS_MOSTRADAS:
        salida.append((comp.nombre, ids))
    return ids


def compuertas_usadas(unidad, tele):
    """[(compuerta, cuántas hay, cuántas se activaron)] en la última operación.
    Una compuerta se 'activa' si alguno de sus transistores recibió señal."""
    global _ESTRUCTURA
    if _ESTRUCTURA is None or _ESTRUCTURA[0] is not unidad:
        lista = []
        for _, comp in componentes(unidad):
            _recolectar(comp, lista)
        _ESTRUCTURA = (unidad, lista)
    total = dict.fromkeys(COMPUERTAS_MOSTRADAS, 0)
    usadas = dict.fromkeys(COMPUERTAS_MOSTRADAS, 0)
    for nombre, ids in _ESTRUCTURA[1]:
        total[nombre] += 1
        if any(i in tele.evaluados for i in ids):
            usadas[nombre] += 1
    return [(n, total[n], usadas[n]) for n in COMPUERTAS_MOSTRADAS]


def compuertas_sin_uso():
    """Lo mismo, pero antes de hacer ninguna operación (todo en 0 usadas)."""
    return compuertas_usadas(ieee754.unidad(), Telemetria())


def contar_primitivas(comp, acc=None):
    """Cuenta cuántas compuertas primitivas (NOT/NAND/NOR) hay dentro de comp."""
    if acc is None:
        acc = {}
    if comp.transistores:  # primitiva: tiene transistores propios
        acc[comp.nombre] = acc.get(comp.nombre, 0) + 1
    for parte in comp.partes:
        contar_primitivas(parte, acc)
    return acc


def resumen_hardware():
    """(filas por componente, conteo de primitivas, total de transistores)."""
    unidad = ieee754.unidad()  # se construye la primera vez que se pide
    filas = []
    primitivas = {}
    for nombre, comp in componentes(unidad):
        filas.append((ETIQUETAS_HARDWARE.get(nombre, nombre), comp.cantidad()))
        contar_primitivas(comp, primitivas)
    return filas, primitivas, Transistor.total


# ---------------------------------------------------------------------------
# Resultado de una operación
# ---------------------------------------------------------------------------

@dataclass
class Resultado:
    simbolo: str
    nombre: str
    a: dict
    b: dict
    r: dict
    coincide: bool
    esperado: float
    total_transistores: int
    usados: int
    conducen: int
    evaluaciones: int
    milisegundos: float
    actividad: list = field(default_factory=list)
    compuertas: list = field(default_factory=list)

    @property
    def texto_resultado(self):
        return texto_valor(self.r["valor"])


class Controlador:
    def operar(self, texto_a, texto_b, simbolo):
        """Hace la operación con el emulador y arma todo lo que se muestra."""
        if simbolo not in OPERACIONES:
            raise ValueError(f"Operación desconocida: {simbolo}")
        a32 = float_a_bits(leer_numero(texto_a))
        b32 = float_a_bits(leer_numero(texto_b))
        nombre, funcion = OPERACIONES[simbolo]

        inicio = time.perf_counter()
        with medir() as tele:
            r32 = funcion(a32, b32)   # <- aquí trabajan los transistores
        ms = (time.perf_counter() - inicio) * 1000

        ca, cb, cr = campos(a32), campos(b32), campos(r32)
        esp32 = esperado_nativo(ca["valor"], cb["valor"], simbolo)
        return Resultado(
            simbolo=simbolo, nombre=nombre, a=ca, b=cb, r=cr,
            coincide=mismos_bits(r32, esp32),
            esperado=bits_a_float(esp32),
            total_transistores=Transistor.total,
            usados=len(tele.evaluados),
            conducen=len(tele.conducen),
            evaluaciones=tele.evaluaciones,
            milisegundos=ms,
            actividad=actividad(ieee754.unidad(), tele),
            compuertas=compuertas_usadas(ieee754.unidad(), tele),
        )


# ---------------------------------------------------------------------------
# Laboratorio de compuertas: qué transistor conduce y por qué
# ---------------------------------------------------------------------------

CATALOGO = {
    "NOT": dict(
        clase=NOT, entradas=("A",), salidas=("Y",),
        texto="NOT (2 transistores): un PMOS arriba (pull-up) y un NMOS abajo "
              "(pull-down). Con A=0 conduce el PMOS y la salida sube a 1; con "
              "A=1 conduce el NMOS y la salida baja a 0."),
    "NAND": dict(
        clase=NAND, entradas=("A", "B"), salidas=("Y",),
        texto="NAND (4 transistores): pull-up = 2 PMOS en paralelo, pull-down = "
              "2 NMOS en serie. La salida solo baja a 0 si A=1 y B=1."),
    "NOR": dict(
        clase=NOR, entradas=("A", "B"), salidas=("Y",),
        texto="NOR (4 transistores): pull-up = 2 PMOS en serie, pull-down = 2 "
              "NMOS en paralelo. La salida solo sube a 1 si A=0 y B=0."),
    "AND": dict(
        clase=AND, entradas=("A", "B"), salidas=("Y",),
        texto="AND (6 transistores) = NAND (4) + NOT (2)."),
    "OR": dict(
        clase=OR, entradas=("A", "B"), salidas=("Y",),
        texto="OR (6 transistores) = NOR (4) + NOT (2)."),
    "XOR": dict(
        clase=XOR, entradas=("A", "B"), salidas=("Y",),
        texto="XOR (16 transistores) = 4 compuertas NAND."),
    "XNOR": dict(
        clase=XNOR, entradas=("A", "B"), salidas=("Y",),
        texto="XNOR (18 transistores) = XOR (16) + NOT (2)."),
    "SumadorCompleto": dict(
        clase=SumadorCompleto, entradas=("A", "B", "Cin"), salidas=("Suma", "Cout"),
        texto="Sumador completo = 2 semisumadores (XOR + AND cada uno) + 1 OR. "
              "Solo con esto ya se superan los 100 transistores."),
}


def _evaluar(gate, entradas):
    """Devuelve siempre una tupla de salidas."""
    if hasattr(gate, "sumar"):
        return tuple(gate.sumar(*entradas))
    return (gate.evaluar(*entradas),)


def probar_compuerta(nombre, entradas):
    """Construye una compuerta NUEVA, la evalúa y devuelve cómo quedó cada
    transistor. No altera el contador global del emulador."""
    info = CATALOGO[nombre]
    guardado = Transistor.total
    Transistor.total = 0          # ids locales 1..n para esta compuerta
    try:
        gate = info["clase"]()
        n = len(info["entradas"])
        verdad = []
        for i in range(2 ** n):   # tabla de verdad completa
            ent = tuple((i >> (n - 1 - k)) & 1 for k in range(n))
            verdad.append((ent, _evaluar(gate, ent)))
        salidas = _evaluar(gate, tuple(entradas))  # la última evaluación manda
    finally:
        Transistor.total = guardado

    base = tabla_transistor_compuerta(gate)
    ts = gate.todos_los_transistores()
    filas = [(ruta, tid, tipo, etq, t.activo)
             for (ruta, tid, tipo, etq), t in zip(base, ts)]
    return {"salidas": salidas, "filas": filas, "verdad": verdad,
            "cantidad": gate.cantidad()}
