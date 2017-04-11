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

u16 testbed_get_drops(struct iphdr *iph, struct testbed_metrics *testbed)
{
    u16 drops;

    if ((iph->tos & 3)) {
        drops = testbed->drops_ecn;
        if (drops > 31) {
            pr_info("Large ecn drops:  %hu\n", drops);
            drops = 31; /* since we can only use 5 bits, max is 32 */
        }
        testbed->drops_ecn -= drops; /* subtract drops we can report, rest is for the following packet */
    } else {
        drops = testbed->drops_nonecn;
        if (drops > 31) {
            pr_info("Large nonecn drops:  %hu\n", drops);
            drops = 31; /* since we can only use 5 bits, max is 32 */
        }
        testbed->drops_nonecn -= drops; /* subtract drops we can report, rest is for the following packet */
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
    u64 qdelay; /* delay-based queue size in ms */

    /* queue delay converted from ns to ms */
    qdelay = ((__force __u64)(ktime_get_real_ns() - ktime_to_ns(skb_get_ktime(skb)))) >> 20;

    ethh = eth_hdr(skb);
    if (ntohs(ethh->h_proto) == ETH_P_IP) {
        iph = ip_hdr(skb);
        id = ntohs(iph->id);
        check = ntohs((__force __be16)iph->check);
        check += id;
        if ((check+1) >> 16) check = (check+1) & 0xffff;
        //  id = (__force __u16)sch->q.qlen;
        if (qdelay > 2047) {
            pr_info("Large queue delay:  %llu\n", qdelay);
            qdelay = 2047;
        }
        id = (__force __u16) qdelay;
        drops = testbed_get_drops(iph, testbed);
        id = id | (drops << 11); /* use upper 5 bits in id field to store number of drops before the current packet */
        check -= id;
        check += check >> 16; /* adjust carry */
        iph->id = htons(id);
        iph->check = (__force __sum16)htons(check);
    }
}
