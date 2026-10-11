"""PERSONA 5 - Interfaz gráfica (Tkinter) del emulador de transistores.

Dos pestañas, pensadas para poder explicarse en pocas frases:
  1. Calculadora: escribes dos números, eliges la operación y ves el resultado,
     cómo queda guardado en IEEE 754 (signo | exponente | mantisa), cuántos
     transistores hay y qué parte del hardware trabajó.
  2. Compuertas: eliges una compuerta, cambias sus entradas y ves qué
     transistor (PMOS/NMOS) conduce y por qué sale ese valor.

La lógica está en controlador.py; este archivo solo dibuja la ventana.
"""
import tkinter as tk
from tkinter import ttk, messagebox

from controlador import (Controlador, OPERACIONES, CATALOGO, probar_compuerta,
                         resumen_hardware, agrupar_actividad, texto_valor,
                         compuertas_sin_uso)

# ---------------------------- colores y fuentes ----------------------------
BG = "#0b1220"          # fondo de la ventana
CARD = "#131c2f"        # fondo de las tarjetas
BORDE = "#25314a"
TXT = "#e5e7eb"
SUAVE = "#8b97ad"       # texto secundario
ACENTO = "#22d3ee"      # cian
BOTON = "#06b6d4"
SELEC = "#0891b2"       # botón/segmento seleccionado
OK = "#4ade80"
MAL = "#f87171"

C_SIGNO = "#f87171"     # rojo: signo
C_EXP = "#fbbf24"       # amarillo: exponente
C_MANT = "#60a5fa"      # azul: mantisa
PMOS = "#3b82f6"
NMOS = "#f59e0b"
APAGADO = "#334155"
COLORES_GRUPO = ["#22d3ee", "#a78bfa", "#f472b6", "#fbbf24"]

F_TEXTO = ("Segoe UI", 10)
F_PEQ = ("Segoe UI", 9)
F_ETIQ = ("Segoe UI", 9, "bold")
F_ENTRADA = ("Segoe UI", 18)
F_BOTON = ("Segoe UI", 12, "bold")
F_RESULTADO = ("Segoe UI", 38, "bold")
F_NUMERO = ("Segoe UI", 28, "bold")
F_MONO = ("Consolas", 10)
F_BITS = ("Consolas", 13, "bold")

EJEMPLOS = [
    ("0.1 + 0.2", "0.1", "+", "0.2"),
    ("1 ÷ 3", "1", "÷", "3"),
    ("-2.5 × 4", "-2.5", "×", "4"),
    ("1 ÷ 0", "1", "÷", "0"),
    ("3.4e38 × 10", "3.4e38", "×", "10"),
]
COMPUERTAS_GRUPOS = ("NOT", "NAND", "NOR", "AND", "OR", "XOR")
SIMBOLO_VISIBLE = {"+": "+", "-": "−", "×": "×", "÷": "÷"}


# ------------------------------ piezas de UI --------------------------------
def tarjeta(padre, titulo=None):
    marco = tk.Frame(padre, bg=CARD, highlightthickness=1,
                     highlightbackground=BORDE)
    if titulo:
        tk.Label(marco, text=titulo, bg=CARD, fg=SUAVE,
                 font=F_ETIQ).pack(anchor="w", padx=14, pady=(10, 2))
    return marco


def etiqueta(padre, texto="", fg=TXT, fuente=F_TEXTO, bg=CARD, **kw):
    return tk.Label(padre, text=texto, fg=fg, bg=bg, font=fuente, **kw)


def campo(padre, variable, ancho=10):
    return tk.Entry(padre, textvariable=variable, width=ancho, font=F_ENTRADA,
                    bg=BG, fg=TXT, insertbackground=TXT, relief="flat",
                    justify="center", highlightthickness=2,
                    highlightbackground=BORDE, highlightcolor=ACENTO)


def boton(padre, texto, comando):
    return tk.Button(padre, text=texto, command=comando, font=F_BOTON,
                     bg=BOTON, fg="#001018", activebackground=ACENTO,
                     activeforeground="#001018", relief="flat", bd=0,
                     padx=22, pady=8, cursor="hand2")


def pastilla(padre, texto, comando):
    return tk.Button(padre, text=texto, command=comando, font=F_PEQ,
                     bg=BORDE, fg=SUAVE, activebackground=SELEC,
                     activeforeground="white", relief="flat", bd=0,
                     padx=10, pady=3, cursor="hand2")


def segmentado(padre, variable, opciones, comando=None, fuente=F_BOTON):
    """Fila de botones tipo interruptor. opciones = [(texto, valor)]."""
    marco = tk.Frame(padre, bg=CARD)
    for texto, valor in opciones:
        tk.Radiobutton(marco, text=texto, value=valor, variable=variable,
                       indicatoron=False, command=comando, font=fuente,
                       bg=BORDE, fg=TXT, selectcolor=SELEC,
                       activebackground=SELEC, activeforeground="white",
                       relief="flat", bd=0, padx=14, pady=6,
                       cursor="hand2").pack(side="left", padx=2)
    return marco


def llenar(arbol, filas, etiquetas=None):
    arbol.delete(*arbol.get_children())
    for i, fila in enumerate(filas):
        tag = (etiquetas[i],) if etiquetas and etiquetas[i] else ()
        arbol.insert("", "end", values=fila, tags=tag)


def crear_arbol(padre, columnas, anchos, alto):
    marco = tk.Frame(padre, bg=CARD)
    arbol = ttk.Treeview(marco, columns=[c[0] for c in columnas],
                         show="headings", height=alto)
    for (cid, titulo), ancho in zip(columnas, anchos):
        arbol.heading(cid, text=titulo)
        arbol.column(cid, width=ancho, anchor="w")
    barra = ttk.Scrollbar(marco, orient="vertical", command=arbol.yview)
    arbol.configure(yscrollcommand=barra.set)
    arbol.pack(side="left", fill="both", expand=True)
    barra.pack(side="right", fill="y")
    return marco, arbol


# --------------------------------- ventana ----------------------------------
class App:
    def __init__(self, raiz, maximizar=True):
        self.raiz = raiz
        self.ctl = Controlador()
        raiz.title("Emulador de transistores CMOS - IEEE 754")
        raiz.geometry("1100x720")
        raiz.minsize(1000, 600)
        raiz.configure(background=BG)
        if maximizar:
            try:
                raiz.state("zoomed")   # maximizada en Windows
            except tk.TclError:
                pass
        self._estilos()

        cab = tk.Frame(raiz, bg=BG)
        cab.pack(fill="x", padx=16, pady=(12, 4))
        tk.Label(cab, text="Emulador de transistores", bg=BG, fg=TXT,
                 font=("Segoe UI", 18, "bold")).pack(side="left")
        tk.Label(cab, text="  CMOS · IEEE 754", bg=BG, fg=ACENTO,
                 font=("Segoe UI", 12)).pack(side="left", pady=(6, 0))

        self.pestanas = ttk.Notebook(raiz)
        self.pestanas.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self._tab_calculadora()
        self._tab_compuertas()
        self.calcular()   # arranca mostrando 0.1 + 0.2

    def _estilos(self):
        e = ttk.Style()
        try:
            e.theme_use("clam")
        except tk.TclError:
            pass
        e.configure("Treeview", font=F_MONO, rowheight=24, background=CARD,
                    fieldbackground=CARD, foreground=TXT, borderwidth=0)
        e.map("Treeview", background=[("selected", SELEC)],
              foreground=[("selected", "white")])
        e.configure("Treeview.Heading", font=F_ETIQ, background=BORDE,
                    foreground=TXT, relief="flat", borderwidth=0)
        e.map("Treeview.Heading", background=[("active", BORDE)])
        e.configure("Vertical.TScrollbar", background=BORDE, troughcolor=CARD,
                    arrowcolor=SUAVE, borderwidth=0)
        e.configure("TNotebook", background=BG, borderwidth=0, bordercolor=BG,
                    lightcolor=BG, darkcolor=BG)
        e.configure("TNotebook.Tab", background=CARD, foreground=SUAVE,
                    padding=(22, 8), font=("Segoe UI", 11), borderwidth=0,
                    bordercolor=BG, lightcolor=CARD, darkcolor=CARD)
        e.map("TNotebook.Tab",
              background=[("selected", SELEC)],
              foreground=[("selected", "white")],
              bordercolor=[("selected", BG)],
              lightcolor=[("selected", SELEC)],
              darkcolor=[("selected", SELEC)])
        try:  # quita el recuadro de foco de las pestañas
            e.layout("TNotebook.Tab", [("Notebook.tab", {"sticky": "nswe",
                "children": [("Notebook.padding", {"side": "top",
                    "sticky": "nswe", "children": [("Notebook.label",
                        {"side": "top", "sticky": ""})]})]})])
        except tk.TclError:
            pass

    # ==================================================================
    # PESTAÑA 1: Calculadora
    # ==================================================================
    def _tab_calculadora(self):
        f = tk.Frame(self.pestanas, bg=BG)
        self.pestanas.add(f, text="Calculadora")
        izq = tk.Frame(f, bg=BG)
        izq.pack(side="left", fill="both", expand=True, padx=(10, 5), pady=10)
        der = tarjeta(f, "TRANSISTORES")
        der.pack(side="left", fill="y", padx=(5, 10), pady=10)

        # ===== columna izquierda =====
        # --- 1. operación ---
        t = tarjeta(izq, "1 · ELIGE LA OPERACIÓN")
        t.pack(fill="x")
        fila = tk.Frame(t, bg=CARD)
        fila.pack(anchor="w", padx=14, pady=(2, 6))
        self.var_a = tk.StringVar(value="0.1")
        self.var_b = tk.StringVar(value="0.2")
        self.var_op = tk.StringVar(value="+")
        campo(fila, self.var_a).pack(side="left", ipady=4)
        segmentado(fila, self.var_op,
                   [(SIMBOLO_VISIBLE[s], s) for s in OPERACIONES],
                   fuente=("Segoe UI", 16, "bold")).pack(side="left", padx=12)
        campo(fila, self.var_b).pack(side="left", ipady=4)
        boton(fila, "Calcular", self.calcular).pack(side="left", padx=16)
        self.raiz.bind("<Return>", lambda _e: self.calcular())

        ej = tk.Frame(t, bg=CARD)
        ej.pack(anchor="w", padx=14, pady=(0, 10))
        etiqueta(ej, "Prueba rápida:", SUAVE, F_PEQ).pack(side="left", padx=(0, 8))
        for texto, a, op, b in EJEMPLOS:
            pastilla(ej, texto,
                     lambda a=a, op=op, b=b: self._ejemplo(a, op, b)
                     ).pack(side="left", padx=3)

        # --- 2. resultado ---
        res = tarjeta(izq, "2 · RESULTADO")
        res.pack(fill="x", pady=8)
        self.lbl_op = etiqueta(res, "", ACENTO, F_ETIQ)
        self.lbl_op.pack(anchor="w", padx=14)
        self.lbl_res = etiqueta(res, "", TXT, ("Segoe UI", 34, "bold"))
        self.lbl_res.pack(anchor="w", padx=14)
        linea = tk.Frame(res, bg=CARD)
        linea.pack(anchor="w", padx=14, pady=(0, 10))
        self.lbl_verif = etiqueta(linea, "", OK, ("Segoe UI", 10, "bold"))
        self.lbl_verif.pack(side="left")
        etiqueta(linea, "   Python solo comprueba; el cálculo lo hacen los transistores.",
                 SUAVE, F_PEQ).pack(side="left")

        # --- 3. cómo queda en IEEE 754 ---
        bits = tarjeta(izq, "3 · ASÍ SE GUARDA EN IEEE 754 (32 bits)")
        bits.pack(fill="x")
        g = tk.Frame(bits, bg=CARD)
        g.pack(anchor="w", padx=14, pady=(2, 10))
        for col, (texto, color) in enumerate([("signo", C_SIGNO),
                                               ("exponente", C_EXP),
                                               ("mantisa", C_MANT)], start=1):
            etiqueta(g, texto, color, F_ETIQ).grid(row=0, column=col, sticky="w",
                                                   padx=3)
        etiqueta(g, "decimal", SUAVE, F_ETIQ).grid(row=0, column=4, sticky="w",
                                                   padx=(16, 0))
        self.tiras = {}
        for i, (clave, nombre) in enumerate([("A", "A"), ("B", "B"),
                                              ("R", "Resultado")], start=1):
            etiqueta(g, nombre, TXT, F_ETIQ, width=9, anchor="w").grid(
                row=i, column=0, pady=2)
            celdas = []
            for col, color in enumerate([C_SIGNO, C_EXP, C_MANT], start=1):
                lbl = tk.Label(g, text="0", bg=color, fg=BG, font=F_BITS,
                               padx=6, pady=1)
                lbl.grid(row=i, column=col, padx=3, pady=2)
                celdas.append(lbl)
            val = etiqueta(g, "", TXT, ("Segoe UI", 12, "bold"))
            val.grid(row=i, column=4, sticky="w", padx=(16, 0))
            tipo = etiqueta(g, "", SUAVE, F_PEQ)
            tipo.grid(row=i, column=5, sticky="w", padx=(10, 0))
            self.tiras[clave] = (*celdas, val, tipo)

        # ===== columna derecha: transistores y hardware =====
        self.lbl_total = etiqueta(der, "—", ACENTO, ("Segoe UI", 30, "bold"))
        self.lbl_total.pack(anchor="w", padx=14)
        etiqueta(der, "transistores en la unidad", SUAVE, F_PEQ).pack(
            anchor="w", padx=14)
        self.lbl_usados = etiqueta(der, "—", OK, ("Segoe UI", 20, "bold"))
        self.lbl_usados.pack(anchor="w", padx=14, pady=(10, 0))
        etiqueta(der, "usados en esta operación", SUAVE, F_PEQ).pack(
            anchor="w", padx=14)
        tk.Frame(der, bg=BORDE, height=1).pack(fill="x", padx=14, pady=12)
        etiqueta(der, "¿QUÉ PARTE DEL HARDWARE TRABAJÓ?", SUAVE, F_ETIQ).pack(
            anchor="w", padx=14, pady=(0, 6))
        self.canvas_barras = tk.Canvas(der, width=372, height=4 * 46 + 4,
                                       bg=CARD, highlightthickness=0)
        self.canvas_barras.pack(padx=14)
        tk.Frame(der, bg=BORDE, height=1).pack(fill="x", padx=14, pady=(10, 8))
        etiqueta(der, "COMPUERTAS ACTIVADAS", SUAVE, F_ETIQ).pack(
            anchor="w", padx=14, pady=(0, 4))
        cuadro = tk.Frame(der, bg=CARD)
        cuadro.pack(anchor="w", padx=14, pady=(0, 12))
        self.lbl_gate = {}
        for i, nombre in enumerate(COMPUERTAS_GRUPOS):
            fila_, col_ = divmod(i, 3)
            celda = tk.Frame(cuadro, bg=CARD)
            celda.grid(row=fila_, column=col_, sticky="w", padx=(0, 14), pady=3)
            etiqueta(celda, nombre, ACENTO if fila_ == 0 else C_EXP,
                     F_ETIQ).pack(anchor="w")
            v = etiqueta(celda, "—", SUAVE, F_MONO)
            v.pack(anchor="w")
            self.lbl_gate[nombre] = v
        etiqueta(der, "Arriba: primitivas CMOS. Abajo: hechas con las anteriores.",
                 SUAVE, F_PEQ).pack(anchor="w", padx=14, pady=(0, 10))

        # estado inicial: unidad construida, nada usado todavía
        filas, primitivas, total = resumen_hardware()
        self.lbl_total.config(text=f"{total:,}")
        self._barras(agrupar_actividad([(n, c, 0, 0) for n, c in filas]))
        self._poner_compuertas(compuertas_sin_uso())

    def _ejemplo(self, a, op, b):
        self.var_a.set(a)
        self.var_op.set(op)
        self.var_b.set(b)
        self.calcular()

    def calcular(self):
        try:
            r = self.ctl.operar(self.var_a.get(), self.var_b.get(),
                                self.var_op.get())
        except ValueError as e:
            messagebox.showwarning("Dato inválido", str(e))
            return
        except Exception as e:  # error inesperado del emulador
            messagebox.showerror("Error en el emulador", repr(e))
            return

        self.lbl_op.config(text=r.nombre.upper())
        self.lbl_res.config(text=r.texto_resultado, fg=TXT if r.coincide else MAL)
        if r.coincide:
            self.lbl_verif.config(fg=OK, text="✔ Coincide con Python")
        else:
            self.lbl_verif.config(fg=MAL, text=f"✘ Python esperaba {r.esperado!r}")

        self._poner_bits("A", r.a)
        self._poner_bits("B", r.b)
        self._poner_bits("R", r.r)

        self.lbl_total.config(text=f"{r.total_transistores:,}")
        self.lbl_usados.config(text=f"{r.usados:,}")
        self._barras(agrupar_actividad(r.actividad))
        self._poner_compuertas(r.compuertas)

    def _poner_compuertas(self, lista):
        for nombre, total, usadas in lista:
            self.lbl_gate[nombre].config(text=f"{usadas:,} de {total:,}",
                                         fg=TXT if usadas else SUAVE)

    def _poner_bits(self, clave, c):
        signo, exp, mant, valor, tipo = self.tiras[clave]
        signo.config(text=c["signo"])
        exp.config(text=c["exp"])
        mant.config(text=c["mant"])
        valor.config(text=texto_valor(c["valor"]))
        tipo.config(text="" if c["tipo"] == "normal" else f"({c['tipo']})",
                    fg=C_EXP)

    def _barras(self, grupos):
        """Una barra por grupo de hardware: cuánto de él se usó."""
        c = self.canvas_barras
        c.delete("all")
        ancho = 372
        for i, (nombre, total, usados) in enumerate(grupos):
            y = 2 + i * 46
            c.create_text(0, y + 8, text=nombre, anchor="w", fill=TXT,
                          font=F_TEXTO)
            texto = "sin usar" if not usados else f"{usados:,} de {total:,}"
            c.create_text(ancho, y + 8, text=texto, anchor="e",
                          fill=TXT if usados else SUAVE, font=F_MONO)
            c.create_rectangle(0, y + 22, ancho, y + 34, fill=BORDE, outline="")
            if total and usados:
                largo = max(4, int(ancho * usados / total))
                c.create_rectangle(0, y + 22, largo, y + 34,
                                   fill=COLORES_GRUPO[i % len(COLORES_GRUPO)],
                                   outline="")

    # ==================================================================
    # PESTAÑA 2: Compuertas y transistores
    # ==================================================================
    def _tab_compuertas(self):
        f = tk.Frame(self.pestanas, bg=BG)
        self.pestanas.add(f, text="Compuertas")

        sel = tarjeta(f, "1 · ELIGE UNA COMPUERTA Y SUS ENTRADAS")
        sel.pack(fill="x", padx=10, pady=(10, 6))
        fila = tk.Frame(sel, bg=CARD)
        fila.pack(anchor="w", padx=14, pady=(2, 12))
        self.var_gate = tk.StringVar(value="NAND")
        nombres = [(("Sumador" if n == "SumadorCompleto" else n), n)
                   for n in CATALOGO]
        segmentado(fila, self.var_gate, nombres, self._cambio_compuerta,
                   fuente=("Segoe UI", 11, "bold")).pack(side="left")
        self.marco_entradas = tk.Frame(fila, bg=CARD)
        self.marco_entradas.pack(side="left", padx=24)
        self.vars_in, self.botones_in = [], []

        sal = tarjeta(f, "2 · QUÉ HACEN LOS TRANSISTORES")
        sal.pack(fill="x", padx=10, pady=6)
        self.lbl_desc = etiqueta(sal, "", SUAVE, F_TEXTO, wraplength=1000,
                                 justify="left")
        self.lbl_desc.pack(anchor="w", padx=14)
        self.lbl_salida = etiqueta(sal, "", ACENTO, ("Segoe UI", 22, "bold"))
        self.lbl_salida.pack(anchor="w", padx=14, pady=(4, 0))
        leyenda = tk.Frame(sal, bg=CARD)
        leyenda.pack(anchor="w", padx=14, pady=(2, 4))
        for color, texto in ((PMOS, "PMOS conduce"), (NMOS, "NMOS conduce"),
                             (APAGADO, "no conduce")):
            tk.Label(leyenda, text="  ", bg=color).pack(side="left")
            etiqueta(leyenda, texto, SUAVE, F_PEQ).pack(side="left", padx=(4, 14))
        self.canvas = tk.Canvas(sal, height=44, bg=CARD, highlightthickness=0)
        self.canvas.pack(fill="x", padx=14, pady=(0, 10))

        abajo = tk.Frame(f, bg=BG)
        abajo.pack(fill="both", expand=True, padx=10, pady=(6, 10))
        izq = tarjeta(abajo, "TABLA TRANSISTOR → COMPUERTA")
        izq.pack(side="left", fill="both", expand=True)
        marco, self.arbol_trans = crear_arbol(
            izq, [("ruta", "Compuerta"), ("id", "ID"), ("tipo", "Tipo"),
                  ("cond", "¿Conduce?")], [300, 50, 80, 90], 6)
        marco.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.arbol_trans.tag_configure("si", background="#14532d",
                                       foreground="#bbf7d0")

        self.der = tarjeta(abajo, "TABLA DE VERDAD")
        self.der.pack(side="left", fill="y", padx=(8, 0))
        self.arbol_verdad = None
        self._cambio_compuerta()

    def _cambio_compuerta(self):
        info = CATALOGO[self.var_gate.get()]
        for w in self.marco_entradas.winfo_children():
            w.destroy()
        self.vars_in, self.botones_in = [], []
        for nombre in info["entradas"]:
            var = tk.IntVar(value=0)
            b = tk.Checkbutton(self.marco_entradas, text=f"{nombre} = 0",
                               variable=var, indicatoron=False,
                               font=("Segoe UI", 12, "bold"), bg=BORDE, fg=TXT,
                               selectcolor=SELEC, activebackground=SELEC,
                               activeforeground="white", relief="flat", bd=0,
                               padx=16, pady=6, cursor="hand2",
                               command=self._probar_compuerta)
            b.pack(side="left", padx=4)
            self.vars_in.append(var)
            self.botones_in.append((b, nombre))

        if self.arbol_verdad is not None:
            self.arbol_verdad.master.destroy()
        cols = list(info["entradas"]) + list(info["salidas"])
        marco, self.arbol_verdad = crear_arbol(
            self.der, [(c, c) for c in cols], [64] * len(cols), 6)
        marco.pack(fill="y", expand=True, padx=10, pady=(0, 10))
        self.arbol_verdad.tag_configure("actual", background="#78350f",
                                        foreground="#fde68a")
        self.lbl_desc.config(text=info["texto"])
        self._probar_compuerta()

    def _probar_compuerta(self):
        nombre = self.var_gate.get()
        info = CATALOGO[nombre]
        entradas = [v.get() for v in self.vars_in]
        for (boton_, n), v in zip(self.botones_in, entradas):
            boton_.config(text=f"{n} = {v}")
        r = probar_compuerta(nombre, entradas)

        salidas = "   ".join(f"{n} = {v}" for n, v in zip(info["salidas"],
                                                          r["salidas"]))
        self.lbl_salida.config(text=f"{salidas}     ({r['cantidad']} transistores)")

        filas, tags = [], []
        for ruta, tid, tipo, _etq, activo in r["filas"]:
            filas.append((ruta, tid, tipo, "SÍ" if activo else "no"))
            tags.append("si" if activo else "")
        llenar(self.arbol_trans, filas, tags)
        self._dibujar_chips(r["filas"])

        verdad, tags = [], []
        for ent, sal in r["verdad"]:
            verdad.append(tuple(ent) + tuple(sal))
            tags.append("actual" if list(ent) == entradas else "")
        llenar(self.arbol_verdad, verdad, tags)

    def _dibujar_chips(self, filas):
        """Un cuadrito por transistor: se ilumina si conduce."""
        ancho, alto, por_fila = 40, 28, 22
        self.canvas.delete("all")
        n_filas = (len(filas) + por_fila - 1) // por_fila
        self.canvas.config(height=n_filas * (alto + 6) + 4)
        for i, (_ruta, tid, tipo, _etq, activo) in enumerate(filas):
            x = 2 + (i % por_fila) * (ancho + 6)
            y = 2 + (i // por_fila) * (alto + 6)
            color = PMOS if tipo == "PMOS" else NMOS
            self.canvas.create_rectangle(
                x, y, x + ancho, y + alto, fill=color if activo else APAGADO,
                outline=color, width=2)
            self.canvas.create_text(x + ancho / 2, y + alto / 2, text=str(tid),
                                    fill="white" if activo else SUAVE,
                                    font=("Consolas", 9, "bold"))


def iniciar():
    raiz = tk.Tk()
    App(raiz)
    raiz.mainloop()


if __name__ == "__main__":
    iniciar()
