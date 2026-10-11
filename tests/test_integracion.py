"""PERSONA 5 - Pruebas de integración: interfaz (controlador) + las 4 capas.

Se compara siempre contra los operadores nativos de Python, que aquí SÍ se
pueden usar porque son solo para verificar.
"""
import itertools
import random

from controlador import (Controlador, CATALOGO, probar_compuerta,
                         resumen_hardware, leer_numero, agrupar_actividad)
from emulador.transistor import Transistor

CTL = Controlador()
SIMBOLOS = ["+", "-", "×", "÷"]


def test_suma_basica():
    r = CTL.operar("0.1", "0.2", "+")
    assert r.coincide
    assert r.texto_resultado == "0.300000012"


def test_cuatro_operaciones_normales():
    casos = [("7.5", "2.25"), ("-3", "4"), ("100", "0.01"),
             ("123456.789", "-0.000123"), ("1", "3")]
    for a, b in casos:
        for op in SIMBOLOS:
            assert CTL.operar(a, b, op).coincide, (a, op, b)


def test_casos_limite():
    casos = [("1", "0", "÷", "inf"), ("-1", "0", "÷", "-inf"),
             ("0", "0", "÷", "NaN"), ("inf", "-inf", "+", "NaN"),
             ("inf", "0", "×", "NaN"), ("3.4e38", "10", "×", "inf"),
             ("5", "5", "-", "0"), ("1e-45", "2", "÷", None),   # desnormalizado
             ("1e-30", "1e-30", "×", "0"), ("nan", "1", "+", "NaN")]
    for a, b, op, texto in casos:
        r = CTL.operar(a, b, op)
        assert r.coincide, (a, op, b)
        if texto is not None:
            assert r.texto_resultado == texto, (a, op, b, r.texto_resultado)


def test_aleatorios_contra_python():
    random.seed(7)
    for _ in range(60):
        a = repr(random.uniform(-1e4, 1e4))
        b = repr(random.uniform(-1e4, 1e4))
        for op in SIMBOLOS:
            assert CTL.operar(a, b, op).coincide, (a, op, b)


def test_entradas_invalidas():
    for malo in ("abc", "", "  ", "1.2.3"):
        try:
            leer_numero(malo)
        except ValueError:
            continue
        raise AssertionError(f"debió rechazar {malo!r}")
    assert leer_numero("1,5") == 1.5  # coma decimal


def test_contador_de_transistores():
    r = CTL.operar("1", "2", "+")
    assert r.total_transistores >= 100          # requisito del profesor
    assert r.total_transistores == Transistor.total
    assert 0 < r.conducen <= r.usados <= r.total_transistores


def test_la_suma_no_usa_el_multiplicador():
    suma = CTL.operar("1.5", "2.5", "+")
    mult = CTL.operar("1.5", "2.5", "×")
    fila = lambda r: [f for f in r.actividad if f[0].startswith("Multiplicador")][0]
    assert fila(suma)[2] == 0        # ningún transistor usado en la suma
    assert fila(mult)[2] > 0         # en la multiplicación sí


def test_laboratorio_tablas_de_verdad():
    esperado = {
        "NOT": lambda a: (1 - a,),
        "NAND": lambda a, b: (1 - (a & b),),
        "NOR": lambda a, b: (1 - (a | b),),
        "AND": lambda a, b: (a & b,),
        "OR": lambda a, b: (a | b,),
        "XOR": lambda a, b: (a ^ b,),
        "XNOR": lambda a, b: (1 - (a ^ b),),
        "SumadorCompleto": lambda a, b, c: ((a ^ b ^ c), (a & b) | (c & (a ^ b))),
    }
    total_antes = Transistor.total
    for nombre, info in CATALOGO.items():
        n = len(info["entradas"])
        for ent in itertools.product((0, 1), repeat=n):
            r = probar_compuerta(nombre, ent)
            assert r["salidas"] == esperado[nombre](*ent), (nombre, ent)
    assert Transistor.total == total_antes     # el laboratorio no ensucia el contador


def test_laboratorio_cantidad_de_transistores():
    cuentas = {"NOT": 2, "NAND": 4, "NOR": 4, "AND": 6, "OR": 6, "XOR": 16,
               "XNOR": 18}
    for nombre, n in cuentas.items():
        r = probar_compuerta(nombre, (0,) * len(CATALOGO[nombre]["entradas"]))
        assert r["cantidad"] == n and len(r["filas"]) == n, nombre


def test_cmos_pull_up_y_pull_down_nunca_juntos():
    """En una primitiva, PMOS y NMOS que 'ganan' no pueden ser simultáneos."""
    for nombre in ("NOT", "NAND", "NOR"):
        n = len(CATALOGO[nombre]["entradas"])
        for ent in itertools.product((0, 1), repeat=n):
            r = probar_compuerta(nombre, ent)  # _salida() lanza error si hay corto
            assert r["salidas"][0] in (0, 1)


def test_resumen_hardware():
    filas, primitivas, total = resumen_hardware()
    assert total == Transistor.total >= 100
    # El contador global también cuenta lo que crearon otras pruebas, así que
    # se compara contra los transistores de la propia unidad IEEE 754.
    de_la_unidad = sum(cantidad for _, cantidad in filas)
    assert 100 <= de_la_unidad <= total
    por_gate = {"NOT": 2, "NAND": 4, "NOR": 4}
    assert sum(primitivas[g] * t for g, t in por_gate.items()) == de_la_unidad


def test_agrupar_actividad():
    r = CTL.operar("1.5", "2.5", "×")
    grupos = agrupar_actividad(r.actividad)
    assert len(grupos) == 4
    # no se pierde ningún transistor al agrupar
    assert sum(g[1] for g in grupos) == sum(f[1] for f in r.actividad)
    assert sum(g[2] for g in grupos) == sum(f[2] for f in r.actividad)
    por_nombre = {g[0]: g for g in grupos}
    assert por_nombre["Multiplicador"][2] > 0   # multiplicó
    assert por_nombre["Divisor"][2] == 0        # no dividió


def test_compuertas_activadas():
    suma = {n: (t, u) for n, t, u in CTL.operar("1.5", "2.5", "+").compuertas}
    mult = {n: (t, u) for n, t, u in CTL.operar("1.5", "2.5", "×").compuertas}
    for datos in (suma, mult):
        assert set(datos) == {"NOT", "NAND", "NOR", "AND", "OR", "XOR"}
        for t, u in datos.values():
            assert 0 <= u <= t
    assert suma["XOR"][1] > 0           # sumar usa XOR
    assert mult["AND"][1] > suma["AND"][1]   # multiplicar usa muchas más AND
    # una división por cero apenas activa compuertas (caso especial)
    dz = {n: u for n, _t, u in CTL.operar("1", "0", "÷").compuertas}
    assert sum(dz.values()) < 10


def test_ui_se_construye_y_calcula():
    """Abre la interfaz de verdad (sin mostrarla). Se omite si no hay pantalla."""
    try:
        import tkinter as tk
        raiz = tk.Tk()
    except Exception:
        return
    raiz.withdraw()
    try:
        from ui import App
        app = App(raiz, maximizar=False)
        assert app.lbl_res.cget("text") == "0.300000012"   # cálculo inicial
        app.var_a.set("1"); app.var_op.set("÷"); app.var_b.set("0")
        app.calcular()
        assert app.lbl_res.cget("text") == "inf"
        app.var_a.set("-2.5"); app.var_op.set("×"); app.var_b.set("4")
        app.calcular()
        assert app.lbl_res.cget("text") == "-10"
        for nombre in CATALOGO:                  # laboratorio de compuertas
            app.var_gate.set(nombre)
            app._cambio_compuerta()
    finally:
        raiz.destroy()
