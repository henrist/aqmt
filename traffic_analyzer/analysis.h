#ifndef ANALYSIS_H
#define ANALYSIS_H

#include <string>
#include <map>
#include <pcap.h> /* if this gives you an error try pcap/pcap.h */
#include <pthread.h>
#include <netinet/in.h>
#include <sys/time.h>
#include <string.h>
#include <vector>

#define QS_LIMIT 2048
#define PLOT_MATRIX_DIM QS_LIMIT
#define PDF_UPPERLIM 500
#define MAX_FLOWS 1000000

struct SrcDst {
public:
    SrcDst(uint8_t proto, in_addr_t srcip, uint16_t srcport, in_addr_t dstip, uint16_t dstport)
      : m_proto(proto), m_srcip(srcip), m_srcport(srcport), m_dstip(dstip), m_dstport(dstport) {}

    uint8_t m_proto;
    in_addr_t m_srcip, m_dstip;
    uint16_t m_srcport, m_dstport;

    bool operator<(const SrcDst& rhs) const {
        if (m_proto != rhs.m_proto)
            return m_proto < rhs.m_proto;
        if (m_srcip != rhs.m_srcip)
            return m_srcip < rhs.m_srcip;
        if (m_dstip != rhs.m_dstip)
            return m_dstip < rhs.m_dstip;
        if (m_srcport != rhs.m_srcport)
            return m_srcport < rhs.m_srcport;
        return m_dstport < rhs.m_dstport;
    }

    bool operator==(const SrcDst &rhs) const {
        return m_srcip == rhs.m_srcip &&
               m_dstip == rhs.m_dstip &&
               m_srcport == rhs.m_srcport &&
               m_dstport == rhs.m_dstport;
    }
};

struct FlowData {
public:
    FlowData(uint64_t r, uint32_t d, uint32_t m, uint16_t p) {
        rate = r;
        drops = d;
        marks = m;
        port = p;
    }

    FlowData(){}

    void update(uint32_t r, uint32_t d, uint32_t m) {
        rate += r;
        drops += d;
        marks += m;
    }

    void clear() {
        rate = 0;
        drops = 0;
        marks = 0;
        port = 0;
    }

    uint64_t rate;
    uint32_t drops;
    uint32_t marks;
    uint16_t port;

};

struct FlowMap {
public:
    std::map<SrcDst,FlowData> ecn_rate;
    std::map<SrcDst,FlowData> nonecn_rate;
    void init(){
        ecn_rate.clear();
        nonecn_rate.clear();
        /*for (std::map<SrcDst,FlowData>::iterator it = ecn_rate.begin(); it != ecn_rate.end(); ++it)
            it->second.clear();
        for (std::map<SrcDst,FlowData>::iterator it = nonecn_rate.begin(); it != nonecn_rate.end(); ++it)
            it->second.clear();*/
    }
};

struct QueueSize {
public:
    uint32_t ecn00[QS_LIMIT];
    uint32_t ecn01[QS_LIMIT];
    uint32_t ecn10[QS_LIMIT];
    uint32_t ecn11[QS_LIMIT];

    void init(){
        bzero(ecn00,QS_LIMIT*sizeof(uint32_t));
        bzero(ecn01,QS_LIMIT*sizeof(uint32_t));
        bzero(ecn10,QS_LIMIT*sizeof(uint32_t));
        bzero(ecn11,QS_LIMIT*sizeof(uint32_t));
    }
};

struct DataBlock {
public:
    struct QueueSize qs;
    struct QueueSize d_qs; // total number of drops for each queue size
    struct FlowMap fm;
    uint64_t start; // time in us
    uint64_t last;  // time in us
    uint64_t tot_packets_ecn;
    uint64_t tot_packets_nonecn;

    void init(){
        qs.init();
        d_qs.init();
        fm.init();
        tot_packets_ecn = 0;
        tot_packets_nonecn = 0;
    }
};

struct DemoData {
public:
    bool ipclass;
    std::vector<double> ecn_th;
    std::vector<double> nonecn_th;
    std::vector<double> ecn_w;
    std::vector<double> nonecn_w;

    long long util;
    double rtt_base;
    double rtt_ecn;
    double rtt_nonecn;
    double linkcap;
    double mark_ecn;
    double drop_ecn;
    double mark_nonecn;
    double drop_nonecn;
    double fair_rate;
    double fair_window;
    double alrate_ecn;
    double alrate_nonecn;
    double alw_ecn;
    double alw_nonecn;
    double cbrrate_ecn;
    double cbrrate_nonecn;

    std::vector<double> ll_qsize_y;
    std::vector<double> c_qsize_y;
    double avg_qsize_ll;
    double avg_qsize_c;
    double p99_qsize_ll;
    double p99_qsize_c;
    pthread_mutex_t mutex;
    pthread_cond_t newdata;
    DemoData();
    void init();
};

struct ThreadParam {
public:
    uint64_t packets_captured;
    uint64_t packets_processed;
    uint64_t start;
    pthread_mutex_t m_mutex;
    DataBlock *db1; // used by ProcessPacket
    DataBlock *db2; // used by printInfo
    pcap_t* m_descr;
    uint32_t m_sinterval;
    char* m_folder;
    uint32_t m_nrs;
    bool m_demomode;
    bool ipclass;
    std::array<FlowData, MAX_FLOWS> *fd_pf_ecn;
    std::array<FlowData, MAX_FLOWS> *fd_pf_nonecn;
    std::map<SrcDst,uint32_t> ecn_flows_map;
    std::map<SrcDst,uint32_t> nonecn_flows_map;
    uint32_t nr_ecn_flows;
    uint32_t nr_nonecn_flows;
    DemoData *demo_data;
    ThreadParam(pcap_t* descr, uint32_t sinterval, char* folder, uint32_t nrs, bool ipc, DemoData *demodata);
    void swapDB();
};

uint64_t getStamp();
int start_analysis(char *dev, char *folder, uint32_t sinterval, std::string &pcapfilter, bool ipclass, uint32_t nrs, DemoData *demodata);

#endif // ANALYSIS_H
