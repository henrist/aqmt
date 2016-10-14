#include <stdio.h>
#include <stdlib.h>
#include <iostream>
#include <unistd.h>
#include <fstream>
#include <vector>
#include <math.h>
#include <sstream>
#include <string>
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

struct Results {
    double rtt_d;
    double rtt_r;

    double avgrate_ecn;
    double avgrate_nonecn;
    double p99rate_ecn;
    double p99rate_nonecn;
    double p1rate_ecn;
    double p1rate_nonecn;
    double cvrate_ecn;
    double cvrate_nonecn;
    double rr_static;
    double wr_static;

    double avgwin_ecn;
    double avgwin_nonecn;
    double p99win_ecn;
    double p99win_nonecn;
    double p1win_ecn;
    double p1win_nonecn;
    double cvwin_ecn;
    double cvwin_nonecn;

    double avgqs_ecn;
    double avgqs_nonecn;
    double cvqs_ecn;
    double cvqs_nonecn;
    double p99qs_ecn;
    double p99qs_nonecn;
    double p1qs_ecn;
    double p1qs_nonecn;
    double p25qs_ecn;
    double p25qs_nonecn;
    double p75qs_ecn;
    double p75qs_nonecn;

    double avgdrops_qs_ecn;
    double avgdrops_qs_nonecn;
    double vardrops_qs_ecn;
    double vardrops_qs_nonecn;

    double avgmarks_ecn;
    double varmarks_ecn;

    double p99drops_qs_ecn;
    double p1drops_qs_ecn;

    double p99marks_ecn;
    double p1marks_ecn;

    double p99drops_qs_nonecn;
    double p1drops_qs_nonecn;

    std::vector<double> *samples_rate_ecn;
    std::vector<double> *samples_rate_nonecn;
    std::vector<double> *samples_win_ecn;
    std::vector<double> *samples_win_nonecn;
    std::vector<double> *samples_qs_ecn;
    std::vector<double> *samples_qs_nonecn;
    std::vector<double> *samples_marks_ecn;

    std::vector<double> *samples_drops_qs_ecn;
    std::vector<double> *samples_drops_qs_nonecn;

    double ecn_avg;
    double nonecn_avg;

    uint64_t tot_sent_dropped_ecn;
    uint64_t tot_sent_dropped_nonecn;

    Results() {
        samples_rate_ecn = new std::vector<double>();
        samples_rate_nonecn = new std::vector<double>();
        samples_win_ecn = new std::vector<double>();
        samples_win_nonecn = new std::vector<double>();
        samples_qs_ecn = new std::vector<double>();
        samples_qs_nonecn = new std::vector<double>();
        samples_marks_ecn = new std::vector<double>();

        samples_drops_qs_ecn = new std::vector<double>();
        samples_drops_qs_nonecn = new std::vector<double>();

        rtt_d = 0;
        rtt_r = 0;

        avgrate_ecn = 0;
        avgrate_nonecn = 0;
        p99rate_ecn = 0;
        p99rate_nonecn = 0;
        p1rate_ecn = 0;
        p1rate_nonecn = 0;
        cvrate_ecn = 0;
        cvrate_nonecn = 0;
        rr_static = 0;
        wr_static = 0;
        avgwin_ecn = 0;
        avgwin_nonecn = 0;
        p99win_ecn = 0;
        p99win_nonecn = 0;
        p1win_ecn = 0;
        p1win_nonecn = 0;
        cvwin_ecn = 0;
        cvwin_nonecn = 0;

        avgqs_ecn = 0;
        avgqs_nonecn = 0;
        cvqs_ecn = 0;
        cvqs_nonecn = 0;
        p99qs_ecn = 0;
        p99qs_nonecn = 0;
        p1qs_ecn = 0;
        p1qs_nonecn = 0;
        p25qs_ecn = 0;
        p25qs_nonecn = 0;
        p75qs_ecn = 0;
        p75qs_nonecn = 0;
        avgdrops_qs_ecn = 0;
        avgdrops_qs_nonecn = 0;
        vardrops_qs_ecn = 0;
        vardrops_qs_nonecn = 0;
        avgmarks_ecn = 0;
        varmarks_ecn = 0;
        p99drops_qs_ecn = 0;
        p1drops_qs_ecn = 0;
        p99marks_ecn = 0;
        p1marks_ecn = 0;
        p99drops_qs_nonecn = 0;
        p1drops_qs_nonecn = 0;
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

double variance(std::vector<double> *samples, double *avg_res, double *p99_res, double *p1_res, double *p25_res, double *p75_res) {
    double tot = 0;
    long double sumsq = 0;
    double var = 0;
    double avg = 0;
    uint32_t flowsamples = samples->size();
    *p99_res = 0;

    if (p1_res != NULL)
        *p1_res = 0;
    if (p25_res != NULL)
        *p25_res = 0;
    if (p75_res != NULL)
        *p75_res = 0;

    if (flowsamples > 0) {
        std::sort(samples->begin(), samples->end());
        int index_p99 = percentile(99, samples->size())-1;

        if (index_p99 > samples->size()-1) {
            std::cerr << "wrong p99 index: " << index_p99 << " samples: " << samples->size();
            exit(1);
        }

        *p99_res = samples->at(index_p99);

        if (p1_res != NULL)
            *p1_res = samples->at(percentile(1, samples->size())-1);
        if (p25_res != NULL)
            *p25_res = samples->at(percentile(25, samples->size())-1);
        if (p75_res != NULL)
            *p75_res = samples->at(percentile(75, samples->size())-1);
    }

    for (std::vector<double>::iterator it = samples->begin(); it != samples->end(); ++it) {
        tot += *it;
        sumsq += (long double)*it * *it;
    }

    if (flowsamples > 1) {
        var = ((double(flowsamples) * sumsq) - (tot * tot)) / (double(flowsamples) * double(flowsamples-1));
    }

    avg = tot/flowsamples;
    *avg_res = avg;

    return var;
}

double coeffVar(std::vector<double> *samples, double *avg_res, double *p99_res, double *p1_res, double *p25_res, double *p75_res) {
    double var = variance(samples, avg_res, p99_res, p1_res, p25_res, p75_res);
    double cv = 0;

    if (var > 0 && *avg_res > 0) {
        cv = sqrt(var)/ *avg_res;
    }

    return cv;
}

void QSStat(Results *res, uint32_t d, uint32_t r) {
    if (d > 0) {
        res->cvqs_ecn = coeffVar(res->samples_qs_ecn, &res->avgqs_ecn, &res->p99qs_ecn, &res->p1qs_ecn, &res->p25qs_ecn, &res->p75qs_ecn);
    }

    if (r > 0) {
        res->cvqs_nonecn = coeffVar(res->samples_qs_nonecn, &res->avgqs_nonecn, &res->p99qs_nonecn, &res->p1qs_nonecn, &res->p25qs_nonecn, &res->p75qs_nonecn);
    }
}

void DropsMarksStat(Results *res, uint32_t d, uint32_t r) {
    if (d > 0) {
        res->vardrops_qs_ecn = variance(res->samples_drops_qs_ecn, &res->avgdrops_qs_ecn, &res->p99drops_qs_ecn, &res->p1drops_qs_ecn, NULL, NULL);
        res->varmarks_ecn = variance(res->samples_marks_ecn, &res->avgmarks_ecn, &res->p99marks_ecn, &res->p1marks_ecn, NULL, NULL);
    }

    if (r > 0) {
        res->vardrops_qs_nonecn = variance(res->samples_drops_qs_nonecn, &res->avgdrops_qs_nonecn, &res->p99drops_qs_nonecn, &res->p1drops_qs_nonecn,NULL,NULL);
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
}

void calcUtil(std::string filename_ecn, std::string filename_nonecn, double *util_avg, double *util_p99, double *util_p1, double link_bytes_ps) {
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
    *util_p99 = samples.at(percentile(99,nrs) - 1);
    *util_p1 = samples.at(percentile(1,nrs) - 1);

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
}

void getSamplesRateMarksDrops(std::string folder, Results* res, uint32_t d, uint32_t r) {
    if (d > 0) {
        std::stringstream fn_ecn;
        fn_ecn << folder << "/r_tot_ecn";
        readFileRate(fn_ecn.str(), d, res->samples_rate_ecn, res->samples_win_ecn, res->avgqs_ecn, res->rtt_d);

        std::stringstream fn_ecn_marks;
        fn_ecn_marks << folder << "/m_tot_ecn";
        std::stringstream fn_ecn_tot;
        fn_ecn_tot << folder << "/tot_packets_ecn";
        readFileMarks(fn_ecn_marks.str(), res->samples_marks_ecn, fn_ecn_tot.str());
    }

    if (r > 0) {
        std::stringstream fn_nonecn;
        fn_nonecn << folder << "/r_tot_nonecn";
        readFileRate(fn_nonecn.str(), r, res->samples_rate_nonecn, res->samples_win_nonecn, res->avgqs_nonecn, res->rtt_r);

        std::stringstream fn_nonecn_drops;
        fn_nonecn_drops << folder << "/d_tot_nonecn";
        std::stringstream fn_nonecn_tot;
        fn_nonecn_tot << folder << "/tot_packets_nonecn";
        readFileDrops(fn_nonecn_drops.str(), res->samples_drops_qs_nonecn, fn_nonecn_tot.str());

    }
}
void getSamplesQS(std::string folder, Results *res, uint32_t d, uint32_t r) {
    if (d > 0) {
        std::stringstream fn_ecn;
        fn_ecn << folder << "/qs_drops_ecn_pdf";
        readFileQS(fn_ecn.str(), res->samples_qs_ecn, &res->tot_sent_dropped_ecn);
    }

    if (r > 0) {
        std::stringstream fn_nonecn;
        fn_nonecn << folder << "/qs_drops_nonecn_pdf";
        readFileQS(fn_nonecn.str(), res->samples_qs_nonecn, &res->tot_sent_dropped_nonecn);
    }
}

int main(int argc, char **argv) {
    if (argc < 9) {
        usage(argc,argv);
    }

    std::string folder = argv[1];

    std::string fairness = argv[2];
    int nbrf = atoi(argv[3]);
    int link = atoi(argv[4]);
    int rtt_d = atoi(argv[5]);
    int rtt_r = atoi(argv[6]);

    uint32_t dctcp = atoi(argv[7]);
    uint32_t reno = atoi(argv[8]);

    if (fairness.length() != 1) {
        usage(argc,argv);
    }

    struct Results *res = new Results();
    res->rtt_d = (double)rtt_d;
    res->rtt_r = (double)rtt_r;

    getSamplesQS(folder, res, dctcp, reno);
    QSStat(res, dctcp, reno);
    getSamplesRateMarksDrops(folder, res, dctcp, reno);

    if (dctcp > 0) {
        res->cvrate_ecn = coeffVar(res->samples_rate_ecn, &res->avgrate_ecn, &res->p99rate_ecn, &res->p1rate_ecn, NULL, NULL);
        res->cvwin_ecn = coeffVar(res->samples_win_ecn, &res->avgwin_ecn, &res->p99win_ecn, &res->p1win_ecn, NULL, NULL);
    }

    if (reno > 0) {
        res->cvrate_nonecn = coeffVar(res->samples_rate_nonecn, &res->avgrate_nonecn, &res->p99rate_nonecn, &res->p1rate_nonecn, NULL, NULL);
        res->cvwin_nonecn = coeffVar(res->samples_win_nonecn, &res->avgwin_nonecn, &res->p99win_nonecn, &res->p1win_nonecn, NULL, NULL);
    }

    if (dctcp > 0) {
        res->rr_static = res->avgrate_nonecn/res->avgrate_ecn;
        res->wr_static = res->avgwin_nonecn/res->avgwin_ecn;
    }

    std::ofstream *f_avgrate_ecn = openFileW("/avgrate_ecn", folder);
    if (f_avgrate_ecn->is_open()) {
        *f_avgrate_ecn << res->avgrate_ecn;
        f_avgrate_ecn->close();
    }
    std::ofstream *f_avgrate_nonecn = openFileW("/avgrate_nonecn", folder);
    if (f_avgrate_nonecn->is_open()) {
        *f_avgrate_nonecn << res->avgrate_nonecn;
        f_avgrate_nonecn->close();
    }

    //rPDF(res->samples_rate_ecn, res->samples_rate_nonecn, folder.str(), fairness[0], dctcp, reno, nbrf);
    //dmPDF(res->samples_drops_qs_ecn, res->samples_drops_qs_nonecn, res->samples_marks_ecn, folder.str(), i);

    DropsMarksStat(res, dctcp, reno);
    if (res->p99drops_qs_nonecn > 100) {
        std::cerr << "too high drops p99: " << res->p99drops_qs_nonecn << std::endl;
        exit(1);
    }

    //compressed plots for the paper
    std::ofstream *f_avg99pqs_ecn_2d = openFileW("/avg99pqs_ecn_2d", folder);
    std::ofstream *f_avg99pqs_nonecn_2d = openFileW("/avg99pqs_nonecn_2d", folder);

    std::ofstream *f_avgstddevrate_ecn_2d = openFileW("/avgstddevrate_ecn_2d", folder);
    std::ofstream *f_avgstddevrate_nonecn_2d = openFileW("/avgstddevrate_nonecn_2d", folder);

    std::ofstream *f_avgstddevwin_ecn_2d = openFileW("/avgstddevwin_ecn_2d", folder);
    std::ofstream *f_avgstddevwin_nonecn_2d = openFileW("/avgstddevwin_nonecn_2d", folder);

    std::ofstream *f_avg99pdrop_ecn_2d = openFileW("/avg99pdrop_ecn_2d", folder);
    std::ofstream *f_avg99pdrop_nonecn_2d = openFileW("/avg99pdrop_nonecn_2d", folder);

    std::ofstream *f_avg99pmark_ecn_2d = openFileW("/avg99pmark_ecn_2d", folder);

    std::ofstream *f_util_2d = openFileW("/util_2d", folder);
    std::ofstream *f_rr_2d = openFileW("/rr_2d", folder);
    std::ofstream *f_wr_2d = openFileW("/wr_2d", folder);

    *f_avg99pqs_ecn_2d << "s" << dctcp  << " " << res->avgqs_ecn << " " << res->p99qs_ecn << " " << res->p1qs_ecn << " " << res->p25qs_ecn << " " << res->p75qs_ecn << " " << (res->cvrate_ecn*res->avgqs_ecn) << std::endl;

    *f_avgstddevrate_ecn_2d << "s" << dctcp <<  " " << res->avgrate_ecn << " " << res->p99rate_ecn << " " << res->p1rate_ecn << " " <<(res->cvrate_ecn*res->avgrate_ecn) << std::endl;
    *f_avgstddevwin_ecn_2d << "s" << dctcp <<  " " << res->avgwin_ecn << " " << res->p99win_ecn << " " << res->p1win_ecn << " " <<(res->cvwin_ecn*res->avgwin_ecn) << std::endl;

    *f_avg99pdrop_ecn_2d << "s" << dctcp <<  " " << res->avgdrops_qs_ecn << " " << res->p99drops_qs_ecn << " " << res->p1drops_qs_ecn << " " << sqrt(res->vardrops_qs_ecn) << std::endl;
    *f_avg99pmark_ecn_2d << "s" << dctcp <<  " " << res->avgmarks_ecn << " " << res->p99marks_ecn << " " << res->p1marks_ecn << " " << sqrt(res->varmarks_ecn) << std::endl;

    *f_avg99pqs_nonecn_2d << "s" << reno <<  " " << res->avgqs_nonecn << " " << res->p99qs_nonecn << " " << res->p1qs_nonecn << " " << res->p25qs_nonecn << " " << res->p75qs_nonecn << " " << (res->cvrate_nonecn*res->avgqs_nonecn) << std::endl;

    *f_avgstddevrate_nonecn_2d << "s" << reno << " " << res->avgrate_nonecn << " " << res->p99rate_nonecn << " " << res->p1rate_nonecn << " " << (res->cvrate_ecn*res->avgrate_nonecn) << std::endl;

    *f_avgstddevwin_nonecn_2d << "s" << reno <<  " " << res->avgwin_nonecn << " " << res->p99win_nonecn << " " << res->p1win_nonecn << " " <<(res->cvwin_nonecn*res->avgwin_nonecn) << std::endl;
    *f_avg99pdrop_nonecn_2d << "s" << reno << " " << res->avgdrops_qs_nonecn << " " << res->p99drops_qs_nonecn << " " << res->p1drops_qs_nonecn << " " << sqrt(res->vardrops_qs_nonecn) << std::endl;
    *f_rr_2d << "s" << dctcp << ":" << "s" << reno << " " << res->rr_static << std::endl;
    *f_wr_2d << "s" << dctcp << ":" << "s" << reno << " " << res->wr_static << std::endl;

    std::stringstream filename_ecn;
    std::stringstream filename_nonecn;

    filename_ecn << folder << "/r_tot_ecn";
    filename_nonecn << folder << "/r_tot_nonecn";

    double util_avg = 0;
    double util_p99 = 0;
    double util_p1 = 0;
    double link_bytes_ps = (double)link*125000;

    calcUtil(filename_ecn.str(), filename_nonecn.str(), &util_avg, &util_p99, &util_p1, link_bytes_ps);
    *f_util_2d << "s" << dctcp  << ":" << "s" << reno <<  " " << util_avg << " " << util_p99 << " " << util_p1 << std::endl;

    return 0;
}
