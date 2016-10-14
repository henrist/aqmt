#include <stdio.h>
#include <stdlib.h>
#include <iostream>
#include <unistd.h>
#include <fstream>
#include <vector>
#include <math.h>
#include <sstream>
#include <string>
#include <map>
#include <unistd.h>
#define __STDC_FORMAT_MACROS
#include <inttypes.h>
#include <string.h>
#include <algorithm>

#define NRSAMPLES 250
#define PDF_BINS 50
#define MAX_QS 100

#define percentile(p, n) (round(float(p)/100*float(n) + float(1)/2))

struct QSDrops {
    uint32_t qs;
    uint32_t drops;
    QSDrops(uint32_t q, uint32_t d) {
        qs = q;
        drops = d;
    }
};

struct Parameters {
    double rtt_d;
    double rtt_r;
    std::string folder;
    uint32_t n_dctcp;
    uint32_t n_reno;
    std::string fairness;
    int nbrf;
    int link;

    Parameters() {
        rtt_d = 0;
        rtt_r = 0;
        folder = "";
        n_dctcp = 0;
        n_reno = 0;
        fairness = "";
        nbrf = 0;
        link = 0;
    }
};

struct Statistics {
    double avg;
    double cv;
    double var;
    std::map<double, double> p; // percentile and its value
    std::vector<double> *samples;

    Statistics() {
        avg = -1;
        cv = -1;
        var = -1;
        samples = new std::vector<double>(); // should be sorted after insertion
    }
};

struct Results {
    struct Statistics *rate_ecn;
    struct Statistics *rate_nonecn;
    struct Statistics *win_ecn;
    struct Statistics *win_nonecn;
    struct Statistics *qs_ecn;
    struct Statistics *qs_nonecn;
    struct Statistics *drops_qs_ecn;
    struct Statistics *drops_qs_nonecn;
    struct Statistics *marks_ecn;
    struct Statistics *util; // utilization

    double rr_static;
    double wr_static;

    double ecn_avg;
    double nonecn_avg;

    uint64_t tot_sent_dropped_ecn;
    uint64_t tot_sent_dropped_nonecn;

    Results() {
        rate_ecn = new Statistics();
        rate_nonecn = new Statistics();
        win_ecn = new Statistics();
        win_nonecn = new Statistics();
        qs_ecn = new Statistics();
        qs_nonecn = new Statistics();
        drops_qs_ecn = new Statistics();
        drops_qs_nonecn = new Statistics();
        marks_ecn = new Statistics();

        rr_static = 0;
        wr_static = 0;

        ecn_avg = 0;
        nonecn_avg = 0;

        tot_sent_dropped_ecn = 0;
        tot_sent_dropped_nonecn = 0;
    }
};

void usage(int argc, char* argv[]) {
    printf("Usage: %s <folder> <e=rate_equal|d=dc_unequal> <nbr of flows per row/col> <link> <rtt_d> <rtt_r> <nr dctcp flows> <nr reno flows>\n", argv[0]);
    exit(1);
}

std::ofstream* openFileW(std::string filename, std::string folder) {
    std::string filename_out = folder + filename;
    std::ofstream *f;
    f = new std::ofstream(filename_out.c_str());

    if (!f->is_open()) {
        std::cerr << "error opening file: " << filename_out << std::endl;
        exit(1);
    }

    return f;
}

/* currently not used
void dmPDF(std::vector<double> *samples_drops_ecn, std::vector<double> *samples_drops_nonecn,
        std::vector<double> *samples_marks_ecn, std::string folder, int i) {
    std::ofstream *f_decn_pdf;
    std::ofstream *f_mecn_pdf;

    f_decn_pdf = openFileW("/d_pf_ecn_pdf", folder);
    f_mecn_pdf = openFileW("/m_pf_ecn_pdf", folder);

    std::ofstream *f_dnonecn_pdf = openFileW("/d_pf_nonecn_pdf", folder);
    uint32_t decn_pdf[PDF_BINS];
    uint32_t dnonecn_pdf[PDF_BINS];
    uint32_t mecn_pdf[PDF_BINS];
    bzero(decn_pdf, sizeof(uint32_t)*PDF_BINS);
    bzero(dnonecn_pdf, sizeof(uint32_t)*PDF_BINS);
    bzero(mecn_pdf, sizeof(uint32_t)*PDF_BINS);

    uint32_t max = 0;
    std::sort(samples_drops_ecn->begin(), samples_drops_ecn->end());
    std::sort(samples_drops_nonecn->begin(), samples_drops_nonecn->end());

    if (samples_drops_ecn->back() > max)
        max = samples_drops_ecn->back();
    if (samples_drops_nonecn->back() > max)
        max = samples_drops_nonecn->back();

    uint32_t binsize = max/PDF_BINS;
    uint32_t b;

    for (std::vector<double>::iterator it = samples_drops_ecn->begin(); it != samples_drops_ecn->end(); ++it)
    {
        b = (*it)/binsize;
        if (b >= PDF_BINS)
            b = PDF_BINS - 1;
        decn_pdf[b]++;
    }

    for (std::vector<double>::iterator it = samples_drops_nonecn->begin(); it != samples_drops_nonecn->end(); ++it)
    {
        b = (*it)/binsize;
        if (b >= PDF_BINS)
            b = PDF_BINS - 1;
        dnonecn_pdf[b]++;
    }

    std::sort(samples_marks_ecn->begin(), samples_marks_ecn->end());

    if (samples_marks_ecn->back() > max)
        max = samples_marks_ecn->back();

    binsize = max/PDF_BINS;
    for (std::vector<double>::iterator it = samples_marks_ecn->begin(); it != samples_marks_ecn->end(); ++it)
    {
        b = (*it)/binsize;
        if (b >= PDF_BINS)
            b = PDF_BINS - 1;
        mecn_pdf[b]++;
    }

    for (int i = 0; i < PDF_BINS; ++i) {
        *f_decn_pdf << i << " " << decn_pdf[i] << std::endl;
        *f_mecn_pdf << i << " " << mecn_pdf[i] << std::endl;

        *f_dnonecn_pdf << i << " " << dnonecn_pdf[i] << std::endl;
    }

    f_decn_pdf->close();
    f_mecn_pdf->close();

    f_dnonecn_pdf->close();
}
*/

/* currently not used
void rPDF(std::vector<double> *samples_rate_ecn, std::vector<double> *samples_rate_nonecn, std::string folder, char fairness, int dctcp, int reno, int nbrf) {
    std::ofstream *f_recn_pdf = openFileW("/r_pf_ecn_pdf", folder);
    std::ofstream *f_rnonecn_pdf = openFileW("/r_pf_nonecn_pdf", folder);
    uint32_t recn_pdf[PDF_BINS];
    uint32_t rnonecn_pdf[PDF_BINS];
    bzero(recn_pdf, sizeof(uint32_t)*PDF_BINS);
    bzero(rnonecn_pdf, sizeof(uint32_t)*PDF_BINS);

    uint32_t max = 0;

    max = fairness == 'e' ? dctcp + reno : (dctcp ? dctcp : reno);
    if (max == 0)
        max = 1;

    max = 10000000/max/nbrf;

    uint32_t binsize = max/PDF_BINS;
    uint32_t b;

    for (std::vector<double>::iterator it = samples_rate_ecn->begin(); it != samples_rate_ecn->end(); ++it)
    {
        b = (*it)/binsize;
        if (b >= PDF_BINS)
            b = PDF_BINS - 1;
        recn_pdf[b]++;
    }

    for (std::vector<double>::iterator it = samples_rate_nonecn->begin(); it != samples_rate_nonecn->end(); ++it)
    {
        b = (*it)/binsize;
        if (b >= PDF_BINS)
            b = PDF_BINS - 1;
        rnonecn_pdf[b]++;
    }

    for (int i = 0; i < PDF_BINS; ++i) {
        *f_recn_pdf << i << " " << recn_pdf[i] << std::endl;
        *f_rnonecn_pdf << i << " " << rnonecn_pdf[i] << std::endl;
    }

    f_recn_pdf->close();
    f_rnonecn_pdf->close();
}
*/

void variance(struct Statistics *stats) {
    double tot = 0;
    long double sumsq = 0;
    double var = 0;
    double avg = 0;
    std::vector<double> *samples = stats->samples;
    uint32_t flowsamples = samples->size();

    stats->p[1] = 0;
    stats->p[25] = 0;
    stats->p[75] = 0;
    stats->p[99] = 0;

    if (flowsamples > 0) {
        int index_p99 = percentile(99, samples->size())-1;
        if (index_p99 > samples->size()-1) {
            std::cerr << "wrong p99 index: " << index_p99 << " samples: " << samples->size();
            exit(1);
        }

        stats->p[99] = samples->at(index_p99);
        stats->p[1] = samples->at(percentile(1, samples->size())-1);
        stats->p[25] = samples->at(percentile(25, samples->size())-1);
        stats->p[75] = samples->at(percentile(75, samples->size())-1);
    }

    for (std::vector<double>::iterator it = samples->begin(); it != samples->end(); ++it) {
        tot += *it;
        sumsq += (long double)*it * *it;
    }

    if (flowsamples > 1) {
        var = ((double(flowsamples) * sumsq) - (tot * tot)) / (double(flowsamples) * double(flowsamples-1));
    }

    avg = tot/flowsamples;
    stats->avg = avg;
    stats->var = var;
}

void coeffVar(struct Statistics *stats) {
    variance(stats);

    if (stats->var > 0 && stats->avg > 0) {
        stats->cv = sqrt(stats->var) / stats->avg;
    } else {
        stats->cv = 0;
    }
}

void QSStat(Results *res, Parameters *params) {
    if (params->n_dctcp > 0) {
        coeffVar(res->qs_ecn);
    }

    if (params->n_reno > 0) {
        coeffVar(res->qs_nonecn);
    }
}

void DropsMarksStat(Results *res, Parameters *params) {
    if (params->n_dctcp > 0) {
        variance(res->drops_qs_ecn); // TODO: ignore p25 and p75 ?
        variance(res->marks_ecn); // TODO: ignore p25 and p75 ?
    }

    if (params->n_reno > 0) {
        variance(res->drops_qs_nonecn); // TODO: ignore p25 and p75 ?
    }
}

void readFileMarks(std::string filename_marks, std::vector<double> *samples_marks, std::string filename_tot) {
    std::ifstream infile_marks(filename_marks.c_str());
    std::ifstream infile_tot(filename_tot.c_str());

    double marks;
    double tot_packets;

    for (int s = 0; s < NRSAMPLES; ++s) {
        for (int colnr = 0; colnr < 3; ++colnr) {
            if (infile_marks.eof() || infile_tot.eof()) {
                break;
            }

            infile_marks >> marks;

            if (colnr == 2) {
                infile_tot >> tot_packets;
                double marks_perc = 0;

                if (tot_packets > 0) {
                    marks_perc = marks*100/tot_packets;
                }

                samples_marks->push_back(marks_perc);
            }
        }
    }

    infile_marks.close();
    infile_tot.close();

    std::sort(samples_marks->begin(), samples_marks->end());
}

void readFileDrops(std::string filename_drops, std::vector<double> *samples_drops, std::string filename_tot) {
    std::ifstream infile_drops(filename_drops.c_str());
    std::ifstream infile_tot(filename_tot.c_str());

    double drops;
    double tot_packets;

    for (int s = 0; s < NRSAMPLES; ++s) {
        for (int colnr = 0; colnr < 3; ++colnr) {
            if (infile_drops.eof() || infile_tot.eof()) {
                break;
            }

            infile_drops >> drops;

            if (colnr == 2) {
                infile_tot >> tot_packets;
                double drops_perc = 0;

                if (tot_packets+drops > 0)
                    drops_perc = drops*100/(tot_packets+drops);

                samples_drops->push_back(drops_perc);

                if (drops_perc > 100)
                    std::cout << "too large drops perc: " << drops_perc << std::endl;
            }
        }
    }

    infile_drops.close();
    infile_tot.close();

    std::sort(samples_drops->begin(), samples_drops->end());
}

void readFileRate(std::string filename, int nrflows, std::vector<double> *samples_rate, std::vector<double> *samples_win, double avg_qs, double rtt) {
    std::ifstream infile(filename.c_str());
    double rate;

    for (int s = 0; s < NRSAMPLES; ++s) {
        for(std::string line; getline(infile, line);) {
            std::istringstream iss(line);
            int colnr = 0;

            while (iss >> rate) {
                if (colnr++ >= 2) {
                    samples_rate->push_back(rate);
                    double win = 0;

                    if (avg_qs != 0) {
                        win = rate*(avg_qs+rtt)/1000;
                    }

                    samples_win->push_back(win);
                }
            }

            for (int i = colnr; i < nrflows; ++i) {
                samples_rate->push_back(0);
                samples_win->push_back(0);
            }
        }
    }

    infile.close();

    std::sort(samples_rate->begin(), samples_rate->end());
    std::sort(samples_win->begin(), samples_win->end());
}

void calcUtilization(std::string filename_ecn, std::string filename_nonecn, double *util_avg, double *util_p99, double *util_p1, double link_bytes_ps) {
    std::ifstream infile_ecn(filename_ecn.c_str());
    std::ifstream infile_nonecn(filename_nonecn.c_str());

    std::vector<double> samples;
    double rate_ecn;
    double rate_nonecn;
    double util;
    double util_sum = 0;

    for (int s = 0; s < NRSAMPLES*3; ++s) {
        if (infile_ecn.eof() || infile_nonecn.eof()) {
            break;
        }

        infile_ecn >> rate_ecn;
        infile_nonecn >> rate_nonecn;

        if ((s+1)%3 == 0) {
            util = (rate_ecn+rate_nonecn)*100/link_bytes_ps;
            samples.push_back(util);
            util_sum += util;
        }
    }

    infile_ecn.close();
    infile_nonecn.close();

    std::sort(samples.begin(), samples.end());
    int nrs = samples.size();
    *util_avg = util_sum/nrs;
    *util_p99 = samples.at(percentile(99, nrs) - 1);
    *util_p1 = samples.at(percentile(1, nrs) - 1);
}

void readFileQS(std::string filename, std::vector<double> *samples_qs, uint64_t *tot_sent_dropped) {
    std::ifstream infile(filename.c_str());
    if (!infile.is_open()) {
        std::cerr << "error opening file: " << filename << std::endl;
        return;
    }

    double tot_sent = 0;
    double tot_dropped = 0;
    double nrpackets, drops;
    uint32_t qsize = 0;

    while (!infile.eof() && qsize < MAX_QS) {
        infile >> nrpackets;
        infile >> drops;
        for (int i = 0; i < nrpackets; ++i)
            samples_qs->push_back(qsize);
        tot_sent += nrpackets;
        tot_dropped += drops;
        double drops_qs = 0;
        qsize++;
    }

    infile.close();
    double tot_packets = tot_sent + tot_dropped;
    *tot_sent_dropped = (uint64_t)(tot_sent + tot_dropped);

    std::sort(samples_qs->begin(), samples_qs->end());
}

void getSamplesRateMarksDrops(Results* res, Parameters *params) {
    if (params->n_dctcp > 0) {
        std::string fn_ecn = params->folder + "/r_tot_ecn";
        readFileRate(fn_ecn, params->n_dctcp, res->rate_ecn->samples, res->win_ecn->samples, res->qs_ecn->avg, params->rtt_d);

        std::string fn_ecn_marks = params->folder + "/m_tot_ecn";
        std::string fn_ecn_tot = params->folder + "/tot_packets_ecn";
        readFileMarks(fn_ecn_marks, res->marks_ecn->samples, fn_ecn_tot);
    }

    if (params->n_reno > 0) {
        std::string fn_nonecn = params->folder + "/r_tot_nonecn";
        readFileRate(fn_nonecn, params->n_reno, res->rate_nonecn->samples, res->win_nonecn->samples, res->qs_nonecn->avg, params->rtt_r);

        std::string fn_nonecn_drops = params->folder + "/d_tot_nonecn";
        std::string fn_nonecn_tot = params->folder + "/tot_packets_nonecn";
        readFileDrops(fn_nonecn_drops, res->drops_qs_nonecn->samples, fn_nonecn_tot);
    }
}
void getSamplesQS(Results *res, Parameters *params) {
    if (params->n_dctcp > 0) {
        std::string fn_ecn = params->folder + "/qs_drops_ecn_pdf";
        readFileQS(fn_ecn, res->qs_ecn->samples, &res->tot_sent_dropped_ecn);
    }

    if (params->n_reno > 0) {
        std::string fn_nonecn = params->folder + "/qs_drops_nonecn_pdf";
        readFileQS(fn_nonecn, res->qs_nonecn->samples, &res->tot_sent_dropped_nonecn);
    }
}

void loadParameters(int argc, char **argv, struct Parameters *params) {
    if (argc < 9) {
        usage(argc, argv);
    }

    params->folder = argv[1];
    params->fairness = argv[2];
    params->nbrf = atoi(argv[3]);
    params->link = atoi(argv[4]);
    params->rtt_d = (double) atoi(argv[5]);
    params->rtt_r = (double) atoi(argv[6]);
    params->n_dctcp = atoi(argv[7]);
    params->n_reno = atoi(argv[8]);

    if (params->fairness.length() != 1) {
        usage(argc, argv);
    }
}

int main(int argc, char **argv) {
    struct Parameters *params = new Parameters();
    struct Results *res = new Results();

    loadParameters(argc, argv, params);

    getSamplesQS(res, params);
    QSStat(res, params);
    getSamplesRateMarksDrops(res, params);

    if (params->n_dctcp > 0) {
        coeffVar(res->rate_ecn); // TODO: ignore p25 and p75 ?
        coeffVar(res->win_ecn); // TODO: ignore p25 and p75 ?
    }

    if (params->n_reno > 0) {
        coeffVar(res->rate_nonecn); // TODO: ignore p25 and p75 ?
        coeffVar(res->win_nonecn); // TODO: ignore p25 and p75 ?
    }

    if (params->n_dctcp > 0) {
        res->rr_static = res->rate_nonecn->avg/res->rate_ecn->avg;
        res->wr_static = res->win_nonecn->avg/res->win_ecn->avg;
    }

    std::ofstream *f_avgrate_ecn = openFileW("/avgrate_ecn", params->folder);
    if (f_avgrate_ecn->is_open()) {
        *f_avgrate_ecn << res->rate_ecn->avg;
        f_avgrate_ecn->close();
    }

    std::ofstream *f_avgrate_nonecn = openFileW("/avgrate_nonecn", params->folder);
    if (f_avgrate_nonecn->is_open()) {
        *f_avgrate_nonecn << res->rate_nonecn->avg;
        f_avgrate_nonecn->close();
    }

    //rPDF(res->rate_ecn->samples, res->rate_nonecn->samples, params->folder.str(), params->fairness[0], params->n_dctcp, params->n_reno, params->nbrf);
    //dmPDF(res->drops_qs_ecn->samples, res->drops_qs_nonecn->samples, res->marks_ecn->samples, params->folder.str(), i);

    DropsMarksStat(res, params);
    if (res->drops_qs_nonecn->p[99] > 100) {
        std::cerr << "too high drops p99: " << res->drops_qs_nonecn->p[99] << std::endl;
        exit(1);
    }

    //compressed plots for the paper
    std::ofstream *f_avg99pqs_ecn_2d = openFileW("/avg99pqs_ecn_2d", params->folder);
    std::ofstream *f_avg99pqs_nonecn_2d = openFileW("/avg99pqs_nonecn_2d", params->folder);

    std::ofstream *f_avgstddevrate_ecn_2d = openFileW("/avgstddevrate_ecn_2d", params->folder);
    std::ofstream *f_avgstddevrate_nonecn_2d = openFileW("/avgstddevrate_nonecn_2d", params->folder);

    std::ofstream *f_avgstddevwin_ecn_2d = openFileW("/avgstddevwin_ecn_2d", params->folder);
    std::ofstream *f_avgstddevwin_nonecn_2d = openFileW("/avgstddevwin_nonecn_2d", params->folder);

    std::ofstream *f_avg99pdrop_ecn_2d = openFileW("/avg99pdrop_ecn_2d", params->folder);
    std::ofstream *f_avg99pdrop_nonecn_2d = openFileW("/avg99pdrop_nonecn_2d", params->folder);

    std::ofstream *f_avg99pmark_ecn_2d = openFileW("/avg99pmark_ecn_2d", params->folder);

    std::ofstream *f_util_2d = openFileW("/util_2d", params->folder);
    std::ofstream *f_rr_2d = openFileW("/rr_2d", params->folder);
    std::ofstream *f_wr_2d = openFileW("/wr_2d", params->folder);

    *f_avg99pqs_ecn_2d << "s" << params->n_dctcp  << " " << res->qs_ecn->avg << " " << res->qs_ecn->p[99] << " " << res->qs_ecn->p[1] << " " << res->qs_ecn->p[25] << " " << res->qs_ecn->p[75] << " " << (res->rate_ecn->cv*res->qs_ecn->avg) << std::endl;
    *f_avg99pqs_nonecn_2d << "s" << params->n_reno <<  " " << res->qs_nonecn->avg << " " << res->qs_nonecn->p[99] << " " << res->qs_nonecn->p[1] << " " << res->qs_nonecn->p[25] << " " << res->qs_nonecn->p[75] << " " << (res->rate_nonecn->cv*res->qs_nonecn->avg) << std::endl;

    *f_avgstddevrate_ecn_2d << "s" << params->n_dctcp <<  " " << res->rate_ecn->avg << " " << res->rate_ecn->p[99] << " " << res->rate_ecn->p[1] << " " <<(res->rate_ecn->cv*res->rate_ecn->avg) << std::endl;
    *f_avgstddevrate_nonecn_2d << "s" << params->n_reno << " " << res->rate_nonecn->avg << " " << res->rate_nonecn->p[99] << " " << res->rate_nonecn->p[1] << " " << (res->rate_ecn->cv*res->rate_nonecn->avg) << std::endl;

    *f_avgstddevwin_ecn_2d << "s" << params->n_dctcp <<  " " << res->win_ecn->avg << " " << res->win_ecn->p[99] << " " << res->win_ecn->p[1] << " " <<(res->win_ecn->cv*res->win_ecn->avg) << std::endl;
    *f_avgstddevwin_nonecn_2d << "s" << params->n_reno <<  " " << res->win_nonecn->avg << " " << res->win_nonecn->p[99] << " " << res->win_nonecn->p[1] << " " <<(res->win_nonecn->cv*res->win_nonecn->avg) << std::endl;

    *f_avg99pdrop_ecn_2d << "s" << params->n_dctcp <<  " " << res->drops_qs_ecn->avg << " " << res->drops_qs_ecn->p[99] << " " << res->drops_qs_ecn->p[1] << " " << sqrt(res->drops_qs_ecn->var) << std::endl;
    *f_avg99pdrop_nonecn_2d << "s" << params->n_reno << " " << res->drops_qs_nonecn->avg << " " << res->drops_qs_nonecn->p[99] << " " << res->drops_qs_nonecn->p[1] << " " << sqrt(res->drops_qs_nonecn->var) << std::endl;

    *f_avg99pmark_ecn_2d << "s" << params->n_dctcp <<  " " << res->marks_ecn->avg << " " << res->marks_ecn->p[99] << " " << res->marks_ecn->p[1] << " " << sqrt(res->marks_ecn->var) << std::endl;

    *f_rr_2d << "s" << params->n_dctcp << ":" << "s" << params->n_reno << " " << res->rr_static << std::endl;
    *f_wr_2d << "s" << params->n_dctcp << ":" << "s" << params->n_reno << " " << res->wr_static << std::endl;

    std::string filename_ecn = params->folder + "/r_tot_ecn";
    std::string filename_nonecn = params->folder + "/r_tot_nonecn";

    double util_avg = 0;
    double util_p99 = 0;
    double util_p1 = 0;
    double link_bytes_ps = (double)params->link*125000;

    calcUtilization(filename_ecn, filename_nonecn, &util_avg, &util_p99, &util_p1, link_bytes_ps);
    *f_util_2d << "s" << params->n_dctcp  << ":" << "s" << params->n_reno <<  " " << util_avg << " " << util_p99 << " " << util_p1 << std::endl;

    return 0;
}
