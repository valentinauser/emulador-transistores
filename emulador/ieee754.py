"""PERSONA 4 - Unidad IEEE 754 (32 bits): 1 signo | 8 exponente | 23 mantisa.

Convención de bits del proyecto (ver utils.py): lista de 0/1 con el índice 0
como bit MENOS significativo (LSB). Un float de 32 bits queda así:

    bits32[0:23]   -> mantisa (la parte fraccionaria, 23 bits)
    bits32[23:31]  -> exponente (8 bits, guardado con sesgo 127)
    bits32[31]     -> signo (0 = positivo, 1 = negativo)

Regla del equipo: las operaciones (suma, resta, mul, div) usan adders /
multiplier / divider (transistores), NO los operadores + - * / de Python.
'struct' solo se usa en los tests.
"""
from .adders import SumadorN, ComparadorN, RegistroDesplazamiento
from .multiplier import Multiplicador
from .divider import Divisor
from .gates import XOR, AND, OR, NOT
from .utils import entero_a_bits

SESGO = 127

# Tipos de número que puede representar un float de 32 bits
TIPO_CERO = "cero"
TIPO_DESNORMALIZADO = "desnormalizado"
TIPO_NORMAL = "normal"
TIPO_INFINITO = "infinito"
TIPO_NAN = "nan"


# ---------------------------------------------------------------------------
# PARTE 1: decodificar y codificar
# ---------------------------------------------------------------------------

def decodificar(bits32):
    """Separa un float de 32 bits en sus campos.

    Devuelve (signo, exponente, mantisa, tipo):
      - signo:     0 o 1
      - exponente: lista de 8 bits (con sesgo, LSB primero)
      - mantisa:   lista de 23 bits (sin el 1 implícito, LSB primero)
      - tipo:      una de las constantes TIPO_*
    """
    if len(bits32) != 32:
        raise ValueError("Un float de 32 bits debe tener exactamente 32 bits")

    mantisa = bits32[0:23]
    exponente = bits32[23:31]
    signo = bits32[31]

    exp_todo_unos = all(exponente)         # 11111111
    exp_todo_ceros = not any(exponente)    # 00000000
    mantisa_cero = not any(mantisa)

    if exp_todo_unos:
        tipo = TIPO_INFINITO if mantisa_cero else TIPO_NAN
    elif exp_todo_ceros:
        tipo = TIPO_CERO if mantisa_cero else TIPO_DESNORMALIZADO
    else:
        tipo = TIPO_NORMAL

    return signo, exponente[:], mantisa[:], tipo


def codificar(signo, exponente, mantisa):
    """Arma un float de 32 bits a partir de sus campos (inverso de decodificar)."""
    if signo not in (0, 1):
        raise ValueError("El signo debe ser 0 o 1")
    if len(exponente) != 8:
        raise ValueError("El exponente debe tener 8 bits")
    if len(mantisa) != 23:
        raise ValueError("La mantisa debe tener 23 bits")
    return list(mantisa) + list(exponente) + [signo]


def mantisa_con_implicito(mantisa, tipo):
    """Devuelve la mantisa de 24 bits lista para operar.

    - Normal: se agrega el 1 implícito como bit 23 (el más significativo).
    - Cero y desnormalizado: el bit implícito es 0.
    """
    bit_implicito = 1 if tipo == TIPO_NORMAL else 0
    return list(mantisa) + [bit_implicito]


def exponente_efectivo(exponente, tipo):
    """Exponente (8 bits, con sesgo) que se usa en las operaciones.

    Los desnormalizados guardan exponente 0, pero se comportan como si
    fuera 1. Los demás usan el exponente tal cual.
    """
    if tipo == TIPO_DESNORMALIZADO:
        return [1, 0, 0, 0, 0, 0, 0, 0]
    return list(exponente)


# Resultados especiales

def cero(signo=0):
    return codificar(signo, [0] * 8, [0] * 23)


def infinito(signo=0):
    return codificar(signo, [1] * 8, [0] * 23)


def nan():
    # NaN "silencioso": exponente todo 1 y el bit más alto de la mantisa en 1
    return codificar(0, [1] * 8, [0] * 22 + [1])


# ---------------------------------------------------------------------------
# PARTE 2: la unidad aritmética (suma, resta, multiplicación y división)
# ---------------------------------------------------------------------------
# Constantes "cableadas" de 10 bits (los exponentes se calculan con 10 bits y
# complemento a 2 para que quepan sumas y números negativos intermedios).
UNO = entero_a_bits(1, 10)
C126 = entero_a_bits(126, 10)
C127 = entero_a_bits(SESGO, 10)
C255 = entero_a_bits(255, 10)


class UnidadIEEE754:
    """Reúne el hardware (sumadores, multiplicador, divisor, registros) que
    usan las cuatro operaciones. Se construye UNA vez para que el contador de
    transistores sea real.

    Idea central: todas las operaciones terminan en _empaquetar(), que recibe
      - signo
      - E: exponente (10 bits, con sesgo) que corresponde al bit más alto de M
      - M: mantisa de 27 bits = 24 bits de mantisa + guard + round + sticky
    y se encarga de normalizar, redondear (al más cercano, empate al par),
    detectar overflow/underflow y armar los 32 bits.
    """

    def __init__(self):
        self.mult = Multiplicador(24)       # mantisas 24 x 24 -> 48 bits
        self.div = Divisor(50)              # dividendo de 50 bits
        self.sum_exp = SumadorN(10)         # aritmética de exponentes
        self.sum24 = SumadorN(24)           # incremento del redondeo
        self.sum27 = SumadorN(27)           # suma/resta de mantisas
        self.comp_exp = ComparadorN(10)     # comparar exponentes
        self.comp_man = ComparadorN(27)     # comparar mantisas
        self.xor = XOR()                    # signos
        self.and_ = AND()
        self.or_ = OR()                     # bit sticky
        self.not_ = NOT()                   # invertir signo en la resta
        self.reg24 = RegistroDesplazamiento(24)
        self.reg27 = RegistroDesplazamiento(27)

    # ----- piezas pequeñas -------------------------------------------------

    def _or_reducir(self, bits):
        """OR de todos los bits de una lista (para el bit sticky)."""
        acc = 0
        for b in bits:
            acc = self.or_.evaluar(acc, b)
        return acc

    def _sumar_exp(self, a, b):
        return self.sum_exp.sumar(a, b)[0]

    def _restar_exp(self, a, b):
        """Devuelve (a - b, negativo, cero) con los flags del sumador."""
        res, cout = self.sum_exp.restar(a, b)
        _, _, z, n = self.sum_exp.flags(res, cout)
        return res, n, z

    def _leer(self, bits32):
        """Devuelve (signo, tipo, E10, M24) de un operando."""
        signo, exp, mant, tipo = decodificar(bits32)
        E = exponente_efectivo(exp, tipo) + [0, 0]
        M = mantisa_con_implicito(mant, tipo)
        return signo, tipo, E, M

    def _prenormalizar(self, M, E):
        """Para desnormalizados: desplaza la mantisa a la izquierda hasta que
        su bit 23 sea 1, bajando el exponente en cada desplazamiento."""
        self.reg24.cargar(M)
        for _ in range(23):
            if self.reg24.leer()[23] == 1:
                break
            self.reg24.desplazar_izquierda(0)
            E = self._restar_exp(E, UNO)[0]
        return self.reg24.leer(), E

    # ----- normalizar, redondear y empaquetar -------------------------------

    def _empaquetar(self, signo, E, M):
        if not any(M):
            return cero(signo)

        # 1) Si E < 1 el resultado es desnormalizado: se desplaza M a la
        #    derecha (1 - E) lugares y el bit que sale se acumula en sticky.
        _, negativo, _ = self._restar_exp(E, UNO)
        if negativo:
            cuenta = self._restar_exp(UNO, E)[0]
            self.reg27.cargar(M)
            for _ in range(28):
                if not any(cuenta):
                    break
                salio = self.reg27.desplazar_derecha(0)
                bits = self.reg27.leer()
                bits[0] = self.or_.evaluar(bits[0], salio)
                self.reg27.cargar(bits)
                cuenta = self._restar_exp(cuenta, UNO)[0]
            M = self.reg27.leer()
            E = UNO

        # 2) Normalizar: desplazar a la izquierda mientras el bit 26 sea 0 y E > 1
        self.reg27.cargar(M)
        for _ in range(26):
            if self.reg27.leer()[26] == 1:
                break
            res, negativo, es_cero = self._restar_exp(E, UNO)
            if negativo or es_cero:          # E - 1 <= 0  ->  E <= 1
                break
            self.reg27.desplazar_izquierda(0)
            E = res
        M = self.reg27.leer()

        # 3) Redondeo al más cercano, empate al par.
        #    M[26:3] = mantisa de 24 bits, M[2] = guard, M[1] y M[0] = resto.
        lsb, guard = M[3], M[2]
        resto = self.or_.evaluar(M[1], M[0])
        incremento = self.and_.evaluar(guard, self.or_.evaluar(resto, lsb))
        mant, acarreo = self.sum24.sumar(M[3:27], [0] * 24, incremento)
        if acarreo:                          # 1.111...1 + 1 = 10.000...0
            mant = [0] * 23 + [1]
            E = self._sumar_exp(E, UNO)

        # 4) Overflow: E >= 255 -> infinito
        res, _, _ = self._restar_exp(E, C255)
        if res[-1] == 0:
            return infinito(signo)

        # 5) Campos finales: si el bit 23 es 0 es desnormalizado (exponente 0)
        exponente = E[0:8] if mant[23] == 1 else [0] * 8
        return codificar(signo, exponente, mant[0:23])

    # ----- multiplicación ---------------------------------------------------

    def multiplicar(self, a32, b32):
        sa, ta, Ea, Ma = self._leer(a32)
        sb, tb, Eb, Mb = self._leer(b32)
        signo = self.xor.evaluar(sa, sb)

        # Casos especiales
        if ta == TIPO_NAN or tb == TIPO_NAN:
            return nan()
        if ta == TIPO_INFINITO or tb == TIPO_INFINITO:
            if ta == TIPO_CERO or tb == TIPO_CERO:
                return nan()                 # infinito * 0
            return infinito(signo)
        if ta == TIPO_CERO or tb == TIPO_CERO:
            return cero(signo)

        # Mantisas de 24 bits normalizadas -> producto de 48 bits
        Ma, Ea = self._prenormalizar(Ma, Ea)
        Mb, Eb = self._prenormalizar(Mb, Eb)
        P = self.mult.multiplicar(Ma, Mb)

        # Exponente asociado al bit 47 del producto: Ea + Eb - 126
        # (equivale a "sumar menos 127" y luego +1 si el producto es >= 2)
        E = self._restar_exp(self._sumar_exp(Ea, Eb), C126)[0]

        # 48 bits -> 27 bits: los 26 más altos + sticky (OR de los 22 bajos)
        sticky = self._or_reducir(P[0:22])
        M = [sticky] + P[22:48]
        return self._empaquetar(signo, E, M)

    # ----- división ---------------------------------------------------------

    def dividir(self, a32, b32):
        sa, ta, Ea, Ma = self._leer(a32)
        sb, tb, Eb, Mb = self._leer(b32)
        signo = self.xor.evaluar(sa, sb)

        # Casos especiales
        if ta == TIPO_NAN or tb == TIPO_NAN:
            return nan()
        if ta == TIPO_INFINITO:
            return nan() if tb == TIPO_INFINITO else infinito(signo)
        if tb == TIPO_INFINITO:
            return cero(signo)
        if tb == TIPO_CERO:
            return nan() if ta == TIPO_CERO else infinito(signo)
        if ta == TIPO_CERO:
            return cero(signo)

        Ma, Ea = self._prenormalizar(Ma, Ea)
        Mb, Eb = self._prenormalizar(Mb, Eb)

        # Pre-escalado: dividendo = Ma desplazada 26 lugares a la izquierda,
        # así el cociente entero trae los bits fraccionarios que necesitamos.
        dividendo = [0] * 26 + Ma            # 50 bits
        divisor = Mb + [0] * 26              # 50 bits
        cociente, residuo = self.div.dividir(dividendo, divisor)

        # Exponente asociado al bit 26 del cociente: Ea - Eb + 127
        E = self._sumar_exp(self._restar_exp(Ea, Eb)[0], C127)

        # Cociente < 2^27 -> 27 bits; el residuo distinto de 0 es el sticky
        M = cociente[0:27]
        sticky = self._or_reducir(residuo)
        M[0] = self.or_.evaluar(M[0], sticky)
        return self._empaquetar(signo, E, M)

    # ----- suma y resta -----------------------------------------------------

    def sumar(self, a32, b32):
        sa, ta, Ea, Ma = self._leer(a32)
        sb, tb, Eb, Mb = self._leer(b32)

        # Casos especiales
        if ta == TIPO_NAN or tb == TIPO_NAN:
            return nan()
        if ta == TIPO_INFINITO and tb == TIPO_INFINITO:
            if self.xor.evaluar(sa, sb) == 1:
                return nan()                 # infinito - infinito
            return infinito(sa)
        if ta == TIPO_INFINITO:
            return infinito(sa)
        if tb == TIPO_INFINITO:
            return infinito(sb)
        if ta == TIPO_CERO and tb == TIPO_CERO:
            return cero(self.and_.evaluar(sa, sb))
        if ta == TIPO_CERO:
            return list(b32)
        if tb == TIPO_CERO:
            return list(a32)

        # Mantisas de 27 bits (24 + guard, round, sticky)
        Ma = [0, 0, 0] + Ma
        Mb = [0, 0, 0] + Mb

        # Ordenar: el operando de mayor magnitud va primero
        igual, menor, _ = self.comp_exp.comparar(Ea, Eb)
        if igual:
            _, menor, _ = self.comp_man.comparar(Ma, Mb)
        if menor:
            sa, Ea, Ma, sb, Eb, Mb = sb, Eb, Mb, sa, Ea, Ma

        # Alinear: desplazar la mantisa menor a la derecha (Ea - Eb) lugares
        diferencia = self._restar_exp(Ea, Eb)[0]
        self.reg27.cargar(Mb)
        for _ in range(28):
            if not any(diferencia):
                break
            salio = self.reg27.desplazar_derecha(0)
            bits = self.reg27.leer()
            bits[0] = self.or_.evaluar(bits[0], salio)     # sticky
            self.reg27.cargar(bits)
            diferencia = self._restar_exp(diferencia, UNO)[0]
        Mb = self.reg27.leer()

        if self.xor.evaluar(sa, sb) == 0:
            # Mismo signo: se suman las magnitudes
            R, acarreo = self.sum27.sumar(Ma, Mb)
            if acarreo:                      # el acarreo pasa a ser el bit más alto
                self.reg27.cargar(R)
                salio = self.reg27.desplazar_derecha(1)
                bits = self.reg27.leer()
                bits[0] = self.or_.evaluar(bits[0], salio)
                R = bits
                Ea = self._sumar_exp(Ea, UNO)
        else:
            # Signos distintos: mayor - menor (nunca da negativo)
            R, _ = self.sum27.restar(Ma, Mb)
            if not any(R):
                return cero(0)               # x - x = +0
        return self._empaquetar(sa, Ea, R)

    def restar(self, a32, b32):
        """a - b = a + (-b): se invierte el bit de signo de b."""
        if len(b32) != 32:
            raise ValueError("Un float de 32 bits debe tener exactamente 32 bits")
        b_negado = list(b32[0:31]) + [self.not_.evaluar(b32[31])]
        return self.sumar(a32, b_negado)


# La unidad se crea la primera vez que se usa (así el contador de
# transistores solo crece cuando de verdad se necesita).
_UNIDAD = None


def unidad():
    global _UNIDAD
    if _UNIDAD is None:
        _UNIDAD = UnidadIEEE754()
    return _UNIDAD


def float_mul(a32, b32):
    return unidad().multiplicar(a32, b32)


def float_add(a32, b32):
    return unidad().sumar(a32, b32)


def float_sub(a32, b32):
    return unidad().restar(a32, b32)


def float_div(a32, b32):
    return unidad().dividir(a32, b32)