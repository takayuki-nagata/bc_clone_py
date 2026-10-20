try:  # noqa: SIM105
    from typing import ClassVar
except ImportError:  # pragma: no cover - MicroPython has no typing module
    pass


def trunc_div(a: int, b: int) -> int:
    """Integer division truncated towards zero."""
    if (a < 0) ^ (b < 0):
        return -(-a // b) if a < 0 else -(a // -b)
    return a // b


class BCNum:
    """Arbitrary-precision decimal number representation for bc."""

    coeff: int
    scale: int

    _pi_cache: ClassVar[dict[int, int]] = {}

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
        coeff = _isqrt(num)
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
                    digits.append(_zpad(temp % obase, digit_width))
                    temp //= obase
                int_str = "".join(f" {d}" for d in reversed(digits))
        else:
            int_str = ""

        # Fractional part formatting
        if self.scale == 0:
            frac_str = ""
        else:
            num_digits = self.scale if obase == 10 else _obase_digits(self.scale, obase)
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
                frac_str = "." + " ".join(_zpad(d, digit_width) for d in frac_digits)

        result = int_str + frac_str
        if is_negative:
            result = "-" + result
        return result

    def to_fixed(self, prec: int) -> int:
        """Return self as an integer scaled by 10**prec (prec >= self.scale)."""
        factor: int = 10 ** (prec - self.scale)
        return self.coeff * factor

    @classmethod
    def from_fixed(cls, value: int, prec: int, scale: int) -> "BCNum":
        """Convert an integer scaled by 10**prec to a BCNum under scale, truncating to zero."""
        return cls(trunc_div(value, 10 ** (prec - scale)), scale)


def _obase_digits(scale: int, obase: int) -> int:
    """Smallest n with obase**n >= 10**scale, i.e. ceil(scale * log(10, obase))."""
    target = 10**scale
    n = 0
    power = 1
    while power < target:
        power *= obase
        n += 1
    return n


# --- Math Library Functions using integer fixed-point arithmetic ---
# A fixed-point value v at precision p stands for v / 10**p.


def _num_digits(n: int) -> int:
    """Number of decimal digits in abs(n) (1 for zero)."""
    return len(str(abs(n)))


def _num_bits(n: int) -> int:
    """Number of bits in abs(n) (0 for zero); int.bit_length is missing on MicroPython."""
    return 0 if n == 0 else len(bin(abs(n))) - 2


def _isqrt(n: int) -> int:
    """Integer square root of n >= 0 by Newton's method."""
    if n < 2:
        return n
    x = 1 << ((_num_bits(n) + 1) // 2)
    while True:
        y = (x + n // x) // 2
        if y >= x:
            return x
        x = y


def _zpad(n: int, width: int) -> str:
    """Format n zero-padded to width digits."""
    s = str(n)
    return "0" * (width - len(s)) + s


def _atan_inv(n: int, one: int) -> int:
    """Compute atan(1/n) for an integer n > 1 at fixed-point unit one."""
    total = term = one // n
    n_sq = n * n
    k = 1
    sign = 1
    while term:
        term //= n_sq
        k += 2
        sign = -sign
        total += sign * (term // k)
    return total


def _get_pi(prec: int) -> int:
    """Compute pi at precision prec using Machin's formula and cache it."""
    if prec in BCNum._pi_cache:
        return BCNum._pi_cache[prec]
    # Machin's formula: pi/4 = 4*atan(1/5) - atan(1/239), with 10 guard digits
    one = 10 ** (prec + 10)
    pi_val = 4 * (4 * _atan_inv(5, one) - _atan_inv(239, one)) // 10**10
    BCNum._pi_cache[prec] = pi_val
    return pi_val


def _reduce_angle(x: int, prec: int) -> int:
    """Reduce an angle x at precision prec into [-pi, pi]."""
    pi = _get_pi(prec)
    two_pi = 2 * pi
    x %= two_pi
    if x > pi:
        x -= two_pi
    return x


def _fixed_sin_cos(x: int, prec: int, is_cos: bool) -> int:
    """Compute sin(x) or cos(x) at precision prec by its Taylor series."""
    one = 10**prec
    x = _reduce_angle(x, prec)
    x_sq = x * x // one
    term = one if is_cos else x
    k = 0 if is_cos else 1
    total = 0
    while term:
        total += term
        term = trunc_div(-term * x_sq, one * (k + 1) * (k + 2))
        k += 2
    return total


def _fixed_atan(x: int, prec: int) -> int:
    """Compute atan(x) at precision prec using inversion and half-angle reduction."""
    if x == 0:
        return 0
    one = 10**prec

    neg = x < 0
    x = abs(x)

    inv = x > one
    if inv:
        x = one * one // x

    # Half-angle reduction 4 times: atan(x) = 2*atan(x / (1 + sqrt(1 + x^2)))
    for _ in range(4):
        x = x * one // (one + _isqrt(one * one + x * x))

    # Taylor series for small x
    total = 0
    num = x
    x_sq = x * x // one
    k = 1
    sign = 1
    while num:
        total += sign * (num // k)
        num = num * x_sq // one
        k += 2
        sign = -sign

    val = total * 16
    if inv:
        val = _get_pi(prec) // 2 - val
    return -val if neg else val


def _fixed_exp(x: int, prec: int) -> int:
    """Compute exp(x) for x >= 0 at precision prec by halving, Taylor series and squaring."""
    one = 10**prec
    halvings = 0
    while x > one // 2:
        x //= 2
        halvings += 1
    # Each halving loses at most one unit; work with extra digits to absorb the error growth
    total = 0
    term = one
    k = 1
    while term:
        total += term
        term = term * x // (one * k)
        k += 1
    for _ in range(halvings):
        total = total * total // one
    return total


def _fixed_atanh(z: int, one: int) -> int:
    """Compute atanh(z) for |z| < 1 at fixed-point unit one."""
    total = 0
    num = z
    z_sq = z * z // one
    k = 1
    while num:
        total += trunc_div(num, k)
        num = trunc_div(num * z_sq, one)
        k += 2
    return total


def bc_sin(x: BCNum, global_scale: int) -> BCNum:
    """Math sine function."""
    prec = max(x.scale, global_scale) + 15 + _num_digits(x.coeff)
    return BCNum.from_fixed(_fixed_sin_cos(x.to_fixed(prec), prec, False), prec, global_scale)


def bc_cos(x: BCNum, global_scale: int) -> BCNum:
    """Math cosine function."""
    prec = max(x.scale, global_scale) + 15 + _num_digits(x.coeff)
    return BCNum.from_fixed(_fixed_sin_cos(x.to_fixed(prec), prec, True), prec, global_scale)


def bc_atan(x: BCNum, global_scale: int) -> BCNum:
    """Math arctangent function."""
    prec = max(x.scale, global_scale) + 15
    return BCNum.from_fixed(_fixed_atan(x.to_fixed(prec), prec), prec, global_scale)


def bc_ln(x: BCNum, global_scale: int) -> BCNum:
    """Math natural logarithm function."""
    if x.coeff <= 0:
        coeff = -99999999999999999999 * (10**global_scale)
        return BCNum(coeff, global_scale)
    # x = num / den; choose m so that y = x / 2**m lies in (1/2, 2)
    num = x.coeff
    den = 10**x.scale
    m = _num_bits(num) - _num_bits(den)
    prec = max(x.scale, global_scale) + 15 + _num_digits(m)
    one = 10**prec
    y = num * one // (den << m) if m >= 0 else (num << -m) * one // den
    # ln(y) = 2*atanh((y-1)/(y+1)); ln(2) = 2*atanh(1/3)
    ln_y = 2 * _fixed_atanh((y - one) * one // (y + one), one)
    ln_2 = 2 * _fixed_atanh(one // 3, one)
    return BCNum.from_fixed(ln_y + m * ln_2, prec, global_scale)


def bc_exp(x: BCNum, global_scale: int) -> BCNum:
    """Math exponential function."""
    # exp(|x|) has about |x|/ln(10) integer digits, and squaring after halving
    # multiplies the relative error, so carry that many extra digits.
    x_int = abs(trunc_div(x.coeff, 10**x.scale))
    prec = max(x.scale, global_scale) + 15 + x_int * 4343 // 10000 + _num_digits(x_int)
    val = _fixed_exp(abs(x.to_fixed(prec)), prec)
    if x.coeff < 0:
        val = 10 ** (2 * prec) // val
    return BCNum.from_fixed(val, prec, global_scale)


def bc_bessel(n_num: BCNum, x: BCNum, global_scale: int) -> BCNum:
    """Bessel function of the first kind J_n(x)."""
    # Order n is integer
    n = trunc_div(n_num.coeff, 10**n_num.scale) if n_num.scale > 0 else n_num.coeff
    if x.is_zero():
        return BCNum(10**global_scale if n == 0 else 0, global_scale)

    if n < 0:
        sign = (-1) ** (-n)
        n_abs = -n
    else:
        sign = 1
        n_abs = n

    # The series terms grow to about exp(|x|/2)**2 before shrinking; carry those digits too
    x_int = abs(trunc_div(x.coeff, 10**x.scale))
    prec = max(x.scale, global_scale) + 25 + x_int * 4343 // 10000
    one = 10**prec

    x_half = trunc_div(x.to_fixed(prec), 2)
    num = one
    for _ in range(n_abs):
        num = trunc_div(num * x_half, one)
    x_half_sq = x_half * x_half // one

    # sum_m (-1)^m (x/2)^(2m+n) / (m! (n+m)!)
    fact_m = 1
    fact_n_m = 1
    for i in range(2, n_abs + 1):
        fact_n_m *= i
    total = 0
    m = 0
    while True:
        term = trunc_div(num, fact_m * fact_n_m)
        if term == 0:
            break
        total += -term if m % 2 == 1 else term
        m += 1
        num = trunc_div(num * x_half_sq, one)
        fact_m *= m
        fact_n_m *= n_abs + m

    return BCNum.from_fixed(sign * total, prec, global_scale)
