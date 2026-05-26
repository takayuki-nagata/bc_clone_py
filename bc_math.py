import decimal
import math
from typing import ClassVar


def trunc_div(a: int, b: int) -> int:
    """Integer division truncated towards zero."""
    if (a < 0) ^ (b < 0):
        return -(-a // b) if a < 0 else -(a // -b)
    return a // b


class BCNum:
    """Arbitrary-precision decimal number representation for bc."""

    coeff: int
    scale: int

    _pi_cache: ClassVar[dict[int, decimal.Decimal]] = {}

    def __init__(self, coeff: int, scale: int) -> None:
        self.coeff = coeff
        self.scale = max(0, scale)

    @classmethod
    def from_string(cls, num_str: str, ibase: int) -> "BCNum":
        """Parse a numeric constant string under ibase into a BCNum."""
        # Strip backslash-newlines
        num_str = num_str.replace("\\\n", "")
        if "." in num_str:
            int_part, frac_part = num_str.split(".", 1)
        else:
            int_part, frac_part = num_str, ""

        def char_val(c: str) -> int:
            if "0" <= c <= "9":
                return ord(c) - ord("0")
            return ord(c) - ord("A") + 10

        # Calculate integer part value
        int_val = 0
        for c in int_part:
            int_val = int_val * ibase + char_val(c)

        scale_val = len(frac_part)
        if scale_val > 0:
            frac_numerator = 0
            for c in frac_part:
                frac_numerator = frac_numerator * ibase + char_val(c)
            frac_denominator = ibase**scale_val

            # coeff = (int_val * frac_denominator + frac_numerator) * 10**scale_val // frac_denominator
            num = (int_val * frac_denominator + frac_numerator) * (10**scale_val)
            coeff = num // frac_denominator
        else:
            coeff = int_val

        return cls(coeff, scale_val)

    def is_zero(self) -> bool:
        """Return True if the number is mathematically zero."""
        return self.coeff == 0

    def add(self, other: "BCNum") -> "BCNum":
        """Add two BCNum values."""
        sr = max(self.scale, other.scale)
        coeff_a = self.coeff * (10 ** (sr - self.scale))
        coeff_b = other.coeff * (10 ** (sr - other.scale))
        return BCNum(coeff_a + coeff_b, sr)

    def sub(self, other: "BCNum") -> "BCNum":
        """Subtract other from self."""
        sr = max(self.scale, other.scale)
        coeff_a = self.coeff * (10 ** (sr - self.scale))
        coeff_b = other.coeff * (10 ** (sr - other.scale))
        return BCNum(coeff_a - coeff_b, sr)

    def mul(self, other: "BCNum", global_scale: int) -> "BCNum":
        """Multiply two BCNum values under scale."""
        sr = min(self.scale + other.scale, max(global_scale, self.scale, other.scale))
        exact_coeff = self.coeff * other.coeff
        exact_scale = self.scale + other.scale
        diff = exact_scale - sr
        coeff = trunc_div(exact_coeff, 10**diff) if diff > 0 else exact_coeff * 10 ** (-diff)
        return BCNum(coeff, sr)

    def div(self, other: "BCNum", global_scale: int) -> "BCNum":
        """Divide self by other under scale."""
        if other.coeff == 0:
            raise ZeroDivisionError("division by zero")
        sr = global_scale
        shift = other.scale - self.scale + sr
        if shift >= 0:
            num = self.coeff * (10**shift)
            den = other.coeff
        else:
            num = self.coeff
            den = other.coeff * (10**-shift)
        coeff = trunc_div(num, den)
        return BCNum(coeff, sr)

    def mod(self, other: "BCNum", global_scale: int) -> "BCNum":
        """Compute self % other under scale."""
        q = self.div(other, global_scale)
        prod_coeff = q.coeff * other.coeff
        prod_scale = q.scale + other.scale
        prod = BCNum(prod_coeff, prod_scale)
        return self.sub(prod)

    def pow(self, other: "BCNum", global_scale: int) -> "BCNum":
        """Raise self to the power of other under scale."""
        # Convert exponent to integer
        b_val = trunc_div(other.coeff, 10**other.scale) if other.scale > 0 else other.coeff

        if b_val == 0:
            return BCNum(1, 0)

        if b_val > 0:
            sr = min(self.scale * b_val, max(global_scale, self.scale))
            res_coeff = 1
            res_scale = 0
            base_coeff = self.coeff
            base_scale = self.scale
            temp_b = b_val
            while temp_b > 0:
                if temp_b % 2 == 1:
                    res_coeff *= base_coeff
                    res_scale += base_scale
                base_coeff *= base_coeff
                base_scale += base_scale
                temp_b //= 2

            diff = res_scale - sr
            coeff = trunc_div(res_coeff, 10**diff) if diff > 0 else res_coeff * 10 ** (-diff)
            return BCNum(coeff, sr)

        # b_val < 0
        b_abs = -b_val
        res_coeff = 1
        res_scale = 0
        base_coeff = self.coeff
        base_scale = self.scale
        temp_b = b_abs
        while temp_b > 0:
            if temp_b % 2 == 1:
                res_coeff *= base_coeff
                res_scale += base_scale
            base_coeff *= base_coeff
            base_scale += base_scale
            temp_b //= 2

        exact_pow = BCNum(res_coeff, res_scale)
        return BCNum(1, 0).div(exact_pow, global_scale)

    def sqrt(self, global_scale: int) -> "BCNum":
        """Compute the square root of self under scale."""
        if self.coeff < 0:
            raise ValueError("square root of negative number")
        sr = max(self.scale, global_scale)
        shift = 2 * sr - self.scale
        num = self.coeff * (10**shift)
        coeff = math.isqrt(num)
        return BCNum(coeff, sr)

    def length(self) -> "BCNum":
        """Compute the total number of significant decimal digits."""
        int_part = abs(self.coeff) // (10**self.scale)
        val = max(1, self.scale) if int_part == 0 else len(str(int_part)) + self.scale
        return BCNum(val, 0)

    def scale_func(self) -> "BCNum":
        """Return the scale of self."""
        return BCNum(self.scale, 0)

    def format_obase(self, obase: int) -> str:
        """Format the BCNum value as a string in obase."""
        if self.coeff == 0:
            return "0"

        is_negative = self.coeff < 0
        coeff_abs = abs(self.coeff)

        int_part = coeff_abs // (10**self.scale)
        frac_coeff = coeff_abs % (10**self.scale)

        # Integer part formatting
        if int_part > 0:
            if obase <= 16:
                digits = []
                temp = int_part
                while temp > 0:
                    digits.append("0123456789ABCDEF"[temp % obase])
                    temp //= obase
                int_str = "".join(reversed(digits))
            else:
                digit_width = len(str(obase - 1))
                digits = []
                temp = int_part
                while temp > 0:
                    digits.append(f"{temp % obase:0{digit_width}d}")
                    temp //= obase
                int_str = "".join(f" {d}" for d in reversed(digits))
        else:
            int_str = ""

        # Fractional part formatting
        if self.scale == 0:
            frac_str = ""
        else:
            num_digits = math.ceil(self.scale * math.log(10, obase)) if obase != 10 else self.scale
            num = frac_coeff
            den = 10**self.scale
            frac_digits = []
            for _ in range(num_digits):
                num *= obase
                frac_digits.append(num // den)
                num %= den

            if obase <= 16:
                frac_str = "." + "".join("0123456789ABCDEF"[d] for d in frac_digits)
            else:
                digit_width = len(str(obase - 1))
                frac_str = "." + "".join(f"{frac_digits[0]:0{digit_width}d}")
                frac_str += "".join(f" {d:0{digit_width}d}" for d in frac_digits[1:])

        result = int_str + frac_str
        if is_negative:
            result = "-" + result
        return result

    def to_decimal(self, prec: int) -> decimal.Decimal:
        """Convert BCNum to decimal.Decimal under a given precision context."""
        with decimal.localcontext() as ctx:
            ctx.prec = prec
            return decimal.Decimal(self.coeff) * (decimal.Decimal(10) ** -self.scale)

    @classmethod
    def from_decimal(cls, dec_val: decimal.Decimal, scale: int) -> "BCNum":
        """Convert a decimal.Decimal back to a BCNum under scale, truncating to zero."""
        with decimal.localcontext() as ctx:
            ctx.prec = max(100, scale + 20)
            ctx.rounding = decimal.ROUND_DOWN
            scaled = dec_val * (decimal.Decimal(10) ** scale)
            coeff = int(scaled.to_integral_value())
            return cls(coeff, scale)


# --- Math Library Functions using decimal.Decimal ---


def _get_pi(prec: int) -> decimal.Decimal:
    """Compute pi to prec digits using Machin's formula and cache it."""
    if prec in BCNum._pi_cache:
        return BCNum._pi_cache[prec]

    with decimal.localcontext() as ctx:
        ctx.prec = prec + 10

        # Machin's formula: pi/4 = 4*atan(1/5) - atan(1/239)
        def _atan_tiny(x: decimal.Decimal) -> decimal.Decimal:
            total = decimal.Decimal(0)
            term = x
            num = x
            x_sq = x * x
            k = 1
            sign = 1
            while True:
                term = num / k
                if term.is_zero() or total == total + sign * term:
                    break
                total += sign * term
                num *= x_sq
                k += 2
                sign = -sign
            return total

        pi_val = 4 * (4 * _atan_tiny(decimal.Decimal("0.2")) - _atan_tiny(decimal.Decimal(1) / 239))

    res = +pi_val  # Apply current context precision
    BCNum._pi_cache[prec] = res
    return res


def _decimal_sin(x: decimal.Decimal, prec: int) -> decimal.Decimal:
    """Compute sine of x using Taylor series under precision prec."""
    with decimal.localcontext() as ctx:
        ctx.prec = prec + 10
        pi = _get_pi(ctx.prec)
        two_pi = 2 * pi

        # Reduce argument
        x = x % two_pi
        if x > pi:
            x -= two_pi
        elif x < -pi:
            x += two_pi

        total = decimal.Decimal(0)
        term = x
        x_sq = x * x
        num = x
        fact = decimal.Decimal(1)
        k = 1
        sign = 1
        while True:
            term = num / fact
            if term.is_zero() or total == total + sign * term:
                break
            total += sign * term
            num *= x_sq
            fact *= (k + 1) * (k + 2)
            k += 2
            sign = -sign
        return total


def _decimal_cos(x: decimal.Decimal, prec: int) -> decimal.Decimal:
    """Compute cosine of x using Taylor series under precision prec."""
    with decimal.localcontext() as ctx:
        ctx.prec = prec + 10
        pi = _get_pi(ctx.prec)
        two_pi = 2 * pi

        # Reduce argument
        x = x % two_pi
        if x > pi:
            x -= two_pi
        elif x < -pi:
            x += two_pi

        total = decimal.Decimal(0)
        term = decimal.Decimal(1)
        x_sq = x * x
        num = decimal.Decimal(1)
        fact = decimal.Decimal(1)
        k = 0
        sign = 1
        while True:
            term = num / fact
            if term.is_zero() or total == total + sign * term:
                break
            total += sign * term
            num *= x_sq
            fact *= (k + 1) * (k + 2)
            k += 2
            sign = -sign
        return total


def _decimal_atan(x: decimal.Decimal, prec: int) -> decimal.Decimal:
    """Compute arctangent of x using series reduction under precision prec."""
    with decimal.localcontext() as ctx:
        ctx.prec = prec + 10
        if x.is_zero():
            return x

        neg = False
        if x < 0:
            x = -x
            neg = True

        inv = False
        if x > 1:
            x = 1 / x
            inv = True

        # Half-angle reduction 4 times
        for _ in range(4):
            x = x / (1 + (1 + x * x).sqrt())

        # Taylor series for small x
        total = decimal.Decimal(0)
        term = x
        num = x
        x_sq = x * x
        k = 1
        sign = 1
        while True:
            term = num / k
            if term.is_zero() or total == total + sign * term:
                break
            total += sign * term
            num *= x_sq
            k += 2
            sign = -sign

        val = total * 16
        if inv:
            pi = _get_pi(ctx.prec)
            val = pi / 2 - val
        if neg:
            val = -val
        return val


def bc_sin(x: BCNum, global_scale: int) -> BCNum:
    """Math sine function."""
    prec = max(x.scale, global_scale) + 15
    dec_x = x.to_decimal(prec)
    dec_res = _decimal_sin(dec_x, prec)
    return BCNum.from_decimal(dec_res, global_scale)


def bc_cos(x: BCNum, global_scale: int) -> BCNum:
    """Math cosine function."""
    prec = max(x.scale, global_scale) + 15
    dec_x = x.to_decimal(prec)
    dec_res = _decimal_cos(dec_x, prec)
    return BCNum.from_decimal(dec_res, global_scale)


def bc_atan(x: BCNum, global_scale: int) -> BCNum:
    """Math arctangent function."""
    prec = max(x.scale, global_scale) + 15
    dec_x = x.to_decimal(prec)
    dec_res = _decimal_atan(dec_x, prec)
    return BCNum.from_decimal(dec_res, global_scale)


def bc_ln(x: BCNum, global_scale: int) -> BCNum:
    """Math natural logarithm function."""
    if x.coeff <= 0:
        coeff = -99999999999999999999 * (10**global_scale)
        return BCNum(coeff, global_scale)
    prec = max(x.scale, global_scale) + 15
    dec_x = x.to_decimal(prec)
    with decimal.localcontext() as ctx:
        ctx.prec = prec
        dec_res = dec_x.ln()
    return BCNum.from_decimal(dec_res, global_scale)


def bc_exp(x: BCNum, global_scale: int) -> BCNum:
    """Math exponential function."""
    prec = max(x.scale, global_scale) + 15
    dec_x = x.to_decimal(prec)
    with decimal.localcontext() as ctx:
        ctx.prec = prec
        dec_res = dec_x.exp()
    return BCNum.from_decimal(dec_res, global_scale)


def bc_bessel(n_num: BCNum, x: BCNum, global_scale: int) -> BCNum:
    """Bessel function of the first kind J_n(x)."""
    # Order n is integer
    n = trunc_div(n_num.coeff, 10**n_num.scale) if n_num.scale > 0 else n_num.coeff
    prec = max(x.scale, global_scale) + 15
    dec_x = x.to_decimal(prec)

    if dec_x.is_zero():
        res_val = decimal.Decimal(1) if n == 0 else decimal.Decimal(0)
        return BCNum.from_decimal(res_val, global_scale)

    with decimal.localcontext() as ctx:
        ctx.prec = prec + 10

        if n < 0:
            sign = (-1) ** (-n)
            n_abs = -n
        else:
            sign = 1
            n_abs = n

        x_half = dec_x / 2
        term_factor = x_half**n_abs

        total = decimal.Decimal(0)
        m = 0
        fact_m = decimal.Decimal(1)
        fact_n_m = decimal.Decimal(math.factorial(n_abs))
        x_half_sq = x_half * x_half
        num = term_factor

        term = decimal.Decimal(1)
        while True:
            den = fact_m * fact_n_m
            term = num / den
            term_signed = -term if m % 2 == 1 else term
            if term.is_zero() or total == total + term_signed:
                break
            total += term_signed

            m += 1
            num *= x_half_sq
            fact_m *= m
            fact_n_m *= n_abs + m

        dec_res = sign * total

    return BCNum.from_decimal(dec_res, global_scale)
