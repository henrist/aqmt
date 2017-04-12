/* Decode float value
 *
 * fl: Float value
 * m_b: Number of mantissa bits
 * e_b: Number of exponent bits
 */
u32 fl2int(u32 fl, u32 m_b, u32 e_b)
{
	const u32 m_max = 1 << m_b;

	fl &= ((m_max << e_b) - 1);

	if (fl < (m_max << 1)) {
		return fl;
	} else {
		return (((fl & (m_max - 1)) + m_max) << ((fl >> m_b) - 1));
	}
}

/* Encode integer value as float value
 * The value will be rounded down if needed
 *
 * val: Value to convert into a float
 * m_b: Number of mantissa bits
 * e_b: Number of exponent bits
 * r: Variable where the remainder will be stored
 */
u32 int2fl(u32 val, u32 m_b, u32 e_b, u32 *r)
{
	u32 len, exponent, mantissa;
	const u32 max_e = (1 << e_b) - 1;
	const u32 max_m = (1 << m_b) - 1;
	const u32 max_fl = ((max_m << 1) + 1) << (max_e - 1);
	*r = 0;

	if (val < (1 << (m_b + 1))) {
		/* possibly only first exponent included, no encoding needed */
		return val;
	}

	if (val >= max_fl) {
		/* avoid overflow */
		*r = val - max_fl;
		return (1 << (m_b + e_b)) - 1;
	}

	/* number of bits without leading 1 */
	len = (sizeof(u32) * 8) - __builtin_clz(val) - 1;

	exponent = len - m_b;
	mantissa = (val >> exponent) & ((1 << m_b) - 1);
	*r = val & ((1 << exponent) - 1);

	return ((exponent + 1) << m_b) | mantissa;
}
