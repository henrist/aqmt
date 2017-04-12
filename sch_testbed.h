/* This file contains our logic for reporting drops to traffic analyzer
 * and is used by our patched versions of the different schedulers
 * we are using.
 *
 * It is only used for our testbed, and for a final implementation it
 * should not be included.
 */

#include <net/inet_ecn.h>

/* This constant defines whether to include drop/queue level report and other
 * testbed related stuff we only want while developing our scheduler.
 */
#define IS_TESTBED 1

struct testbed_metrics {
    /* When dropping ect0 and ect1 packets we need to treat them the same as
     * dropping a ce packet. If the scheduler is congested, having a seperate
     * counter for ect0/ect1 would mean we need to have packets not being
     * marked to deliver the metric. This is unlikely to happen, and would
     * cause falsy information showing nothing being dropped.
     */
    u16     drops_ecn;
    u16     drops_nonecn;
};

void testbed_metrics_init(struct testbed_metrics *testbed)
{
    testbed->drops_ecn = 0;
    testbed->drops_nonecn = 0;
}

void testbed_inc_drop_count(struct sk_buff *skb, struct testbed_metrics *testbed)
{
    struct iphdr* iph;
    struct ethhdr* ethh;

    ethh = eth_hdr(skb);

    /* TODO: make IPv6 compatible (but we probably won't going to use it in our testbed?) */
    if (ntohs(ethh->h_proto) == ETH_P_IP) {
        iph = ip_hdr(skb);

        if ((iph->tos & 3))
            testbed->drops_ecn++;
        else
            testbed->drops_nonecn++;
    }
}

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

u32 testbed_get_drops(struct iphdr *iph, struct testbed_metrics *testbed)
{
    u32 drops;
    u32 drops_remainder;

    if ((iph->tos & 3)) {
        drops = int2fl(testbed->drops_ecn, 2, 3, &drops_remainder);
        if (drops_remainder > 10) {
            pr_info("High (>10) drops ecn remainder:  %u\n", drops_remainder);
        }
        testbed->drops_ecn = (__force __u16) drops_remainder;
    } else {
        drops = int2fl(testbed->drops_nonecn, 2, 3, &drops_remainder);
        if (drops_remainder > 10) {
            pr_info("High (>10) drops nonecn remainder:  %u\n", drops_remainder);
        }
        testbed->drops_nonecn = (__force __u16) drops_remainder;
    }
    return drops;
}

/* add metrics used by traffic analyzer to packet before dispatching */
void testbed_add_metrics(struct sk_buff *skb, struct testbed_metrics *testbed)
{
    struct iphdr *iph;
    struct ethhdr *ethh;
    u32 check;
    u16 drops;
    u16 id;
    u32 qdelay;
    u32 qdelay_remainder;

    ethh = eth_hdr(skb);
    if (ntohs(ethh->h_proto) == ETH_P_IP) {
        iph = ip_hdr(skb);
        id = ntohs(iph->id);
        check = ntohs((__force __be16)iph->check);
        check += id;
        if ((check+1) >> 16) check = (check+1) & 0xffff;

        /* queue delay is converted from ns to units of 32 us and encoded as float */
        qdelay = ((__force __u64)(ktime_get_real_ns() - ktime_to_ns(skb_get_ktime(skb)))) >> 15;
        qdelay = int2fl(qdelay, 7, 4, &qdelay_remainder);
        if (qdelay_remainder > 10) {
            pr_info("High (>10) queue delay remainder:  %u\n", qdelay_remainder);
        }

        id = (__force __u16) qdelay;
        drops = (__force __u16) testbed_get_drops(iph, testbed);
        id = id | (drops << 11); /* use upper 5 bits in id field to store number of drops before the current packet */

        check -= id;
        check += check >> 16; /* adjust carry */
        iph->id = htons(id);
        iph->check = (__force __sum16)htons(check);
    }
}
