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
#define MAX_QS 2048

#define percentile(p, n) (ceil(float(p)/100*float(n)))

struct Parameters {
    double rtt_d;
    double rtt_r;
    std::string analyzer_folder;
    std::string output_folder;
    uint32_t n_ecn;
    uint32_t n_nonecn;
    double link;

    Parameters() {
        rtt_d = 0;
        rtt_r = 0;
        analyzer_folder = "";
        output_folder = "";
        n_ecn = 0;
        n_nonecn = 0;
        link = 0;
    }
};

class Statistics {
  public:
    Statistics() {
        calculated_variance = false;
        calculated_coeffVar = false;
        _variance = NAN;
        _average = NAN;
        _coeffVar = NAN;
        _samples = NULL;
    }

    void samples(std::vector<double> *new_samples) {
        _samples = new_samples;
        std::sort(_samples->begin(), _samples->end());
    }

    std::vector<double> *samples() {
        return _samples;
    }

    double p(double p) {
        if (_samples != NULL && _samples->size() > 0) {
            return _samples->at(percentile(p, _samples->size()) - 1);
        }

        return NAN;
    }

    double front() {
        if (_samples != NULL && _samples->size() > 0) {
            return _samples->front();
        }

        return NAN;
    }

    double back() {
        if (_samples != NULL && _samples->size() > 0) {
            return _samples->back();
        }

        return NAN;
    }

    double variance() {
        if (_samples != NULL && !calculated_variance) {
            calculate_variance();
        }

        return _variance;
    }

    double average() {
        if (_samples != NULL && !calculated_variance) {
            calculate_variance();
        }

        return _average;
    }

    double coeffVar() {
        if (_samples != NULL && !calculated_coeffVar) {
            calculate_coeffVar();
        }

        return _coeffVar;
    }

    double stddev() {
        return sqrt(variance());
    }

  private:
    bool calculated_variance;
    bool calculated_coeffVar;
    double _variance;
    double _average;
    double _coeffVar;
    std::vector<double> *_samples;

    void calculate_coeffVar() {
        if (variance() > 0 && average() > 0) {
            _coeffVar = stddev() / average();
        } else {
            _coeffVar = 0;
        }

        calculated_coeffVar = true;
    }

    void calculate_variance() {
        double tot = 0;
        long double sumsq = 0;
        uint32_t n_samples = _samples->size();

        for (double val: *_samples) {
            tot += val;
            sumsq += (long double) val * val;
        }

        _variance = NAN;
        if (n_samples > 1) {
            _variance = ((double(n_samples) * sumsq) - (tot * tot)) / (double(n_samples) * double(n_samples - 1));
        }

        _average = tot / n_samples;
        calculated_variance = true;
    }
};

struct Results {
    Statistics *rate_ecn;
    Statistics *rate_nonecn;
    Statistics *win_ecn;
    Statistics *win_nonecn;
    Statistics *qs_ecn;
    Statistics *qs_nonecn;
    Statistics *drops_qs_ecn;
    Statistics *drops_qs_nonecn;
    Statistics *marks_ecn;
    Statistics *util_ecn;
    Statistics *util_nonecn;
    Statistics *util_total;

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
        util_ecn = new Statistics();
        util_nonecn = new Statistics();
        util_total = new Statistics();

        rr_static = NAN;
        wr_static = NAN;

        ecn_avg = NAN;
        nonecn_avg = NAN;

        tot_sent_dropped_ecn = 0;
        tot_sent_dropped_nonecn = 0;
    }
};

struct Parameters *params = new Parameters();
struct Results *res = new Results();

std::ofstream* openFileW(std::string filename) {
    std::string filename_out = params->output_folder + "/" + filename;
    std::ofstream *f;
    f = new std::ofstream(filename_out.c_str());

    if (!f->is_open()) {
        std::cerr << "error opening file: " << filename_out << std::endl;
        exit(1);
    }

    return f;
}

void writeToFile(std::string filename, std::string data) {
    std::ofstream *fs = openFileW(filename);
    *fs << data;
    fs->close();
}

void writeStatistics(std::string filename, Statistics *stats) {
    std::stringstream out;
    out << "# average stddev min p1 p25 p50 p75 p99 max" << std::endl;
    out << stats->average() << " " << stats->stddev() << " "
        << stats->front() << " "
        << stats->p(1) << " " << stats->p(25) << " " << stats->p(50) << " "
        << stats->p(75) << " " << stats->p(99)
        << stats->back() << "" << std::endl;
    writeToFile(filename, out.str());
}

void readFileMarks(std::string filename_marks, Statistics *stats, std::string filename_tot) {
    std::ifstream infile_marks(filename_marks.c_str());
    std::ifstream infile_tot(filename_tot.c_str());

    double marks;
    double tot_packets;
    std::vector<double> *samples = new std::vector<double>();

    for (int s = 0; s < NRSAMPLES; ++s) {
        for (int colnr = 0; colnr < 3; ++colnr) {
            if (infile_marks.eof() || infile_tot.eof())
                break;

            infile_marks >> marks;

            if (colnr == 2) {
                infile_tot >> tot_packets;
                double marks_perc = 0;

                if (tot_packets > 0) {
                    marks_perc = marks * 100 / tot_packets;
                }

                samples->push_back(marks_perc);
            }
        }
    }

    infile_marks.close();
    infile_tot.close();
    stats->samples(samples);
}

void readFileDrops(std::string filename_drops, Statistics *stats, std::string filename_tot) {
    std::ifstream infile_drops(filename_drops.c_str());
    std::ifstream infile_tot(filename_tot.c_str());

    double drops;
    double tot_packets;
    std::vector<double> *samples = new std::vector<double>();

    for (int s = 0; s < NRSAMPLES; ++s) {
        for (int colnr = 0; colnr < 3; ++colnr) {
            if (infile_drops.eof() || infile_tot.eof())
                break;

            infile_drops >> drops;

            if (colnr == 2) {
                infile_tot >> tot_packets;
                double drops_perc = 0;

                if (tot_packets+drops > 0)
                    drops_perc = drops*100/(tot_packets+drops);

                samples->push_back(drops_perc);

                if (drops_perc > 100)
                    std::cout << "too large drops perc: " << drops_perc << std::endl;
            }
        }
    }

    infile_drops.close();
    infile_tot.close();
    stats->samples(samples);
}

void readFileRate(std::string filename, Statistics *stats_rate, Statistics *stats_win, double avg_qs, double rtt) {
    std::ifstream infile(filename.c_str());
    double rate;

    std::vector<double> *samples_rate = new std::vector<double>();
    std::vector<double> *samples_win = new std::vector<double>();

    for (int s = 0; s < NRSAMPLES; ++s) {
        for(std::string line; getline(infile, line);) {
            std::istringstream iss(line);
            int colnr = 0;

            while (iss >> rate) {
                if (colnr++ >= 2) {
                    double win = 0;
                    if (avg_qs != 0) {
                        win = rate*(avg_qs+rtt)/1000;
                    }

                    samples_rate->push_back(rate);
                    samples_win->push_back(win);
                }
            }
        }
    }

    infile.close();
    stats_rate->samples(samples_rate);
    stats_win->samples(samples_win);
}

void getSamplesUtilization() {
    std::string filename_ecn = params->analyzer_folder + "/r_tot_ecn";
    std::string filename_nonecn = params->analyzer_folder + "/r_tot_nonecn";

    std::ifstream infile_ecn(filename_ecn.c_str());
    std::ifstream infile_nonecn(filename_nonecn.c_str());

    std::vector<double> *samples_ecn = new std::vector<double>();
    std::vector<double> *samples_nonecn = new std::vector<double>();
    std::vector<double> *samples_total = new std::vector<double>();
    double rate_ecn;
    double rate_nonecn;
    double util_ecn;
    double util_nonecn;
    double util_total;

    // each line consists of three numbers, and we only want the last number
    for (int s = 0; s < NRSAMPLES*3; ++s) {
        if (infile_ecn.eof() || infile_nonecn.eof()) {
            break;
        }

        infile_ecn >> rate_ecn;
        infile_nonecn >> rate_nonecn;

        if ((s+1)%3 == 0) {
            util_ecn = rate_ecn * 100 / params->link;
            util_nonecn = rate_nonecn * 100 / params->link;
            util_total = (rate_ecn+rate_nonecn) * 100 / params->link;
            samples_ecn->push_back(util_ecn);
            samples_nonecn->push_back(util_nonecn);
            samples_total->push_back(util_total);
        }
    }

    infile_ecn.close();
    infile_nonecn.close();
    res->util_ecn->samples(samples_ecn);
    res->util_nonecn->samples(samples_nonecn);
    res->util_total->samples(samples_total);
}

void readFileQS(std::string filename, Statistics *stats, uint64_t *tot_sent_dropped) {
    std::ifstream infile(filename.c_str());
    if (!infile.is_open()) {
        std::cerr << "error opening file: " << filename << std::endl;
        return;
    }

    double tot_sent = 0;
    double tot_dropped = 0;
    double nrpackets, drops;
    uint32_t qsize = 0;
    std::vector<double> *samples = new std::vector<double>();

    while (!infile.eof() && qsize < MAX_QS) {
        infile >> nrpackets;
        infile >> drops;

        for (int i = 0; i < nrpackets; ++i)
            samples->push_back(qsize);

        tot_sent += nrpackets;
        tot_dropped += drops;
        qsize++;
    }

    infile.close();
    stats->samples(samples);
    *tot_sent_dropped = (uint64_t)(tot_sent + tot_dropped);
}

void getSamplesRateMarksDrops() {
    readFileRate(params->analyzer_folder + "/r_tot_ecn", res->rate_ecn, res->win_ecn, res->qs_ecn->average(), params->rtt_d);
    readFileMarks(params->analyzer_folder + "/m_tot_ecn", res->marks_ecn, params->analyzer_folder + "/tot_packets_ecn");
    readFileDrops(params->analyzer_folder + "/d_tot_ecn", res->drops_qs_ecn, params->analyzer_folder + "/tot_packets_ecn");
    readFileRate(params->analyzer_folder + "/r_tot_nonecn", res->rate_nonecn, res->win_nonecn, res->qs_nonecn->average(), params->rtt_r);
    readFileDrops(params->analyzer_folder + "/d_tot_nonecn", res->drops_qs_nonecn, params->analyzer_folder + "/tot_packets_nonecn");
}

void getSamplesQS() {
    readFileQS(params->analyzer_folder + "/qs_drops_ecn_pdf", res->qs_ecn, &res->tot_sent_dropped_ecn);
    readFileQS(params->analyzer_folder + "/qs_drops_nonecn_pdf", res->qs_nonecn, &res->tot_sent_dropped_nonecn);
}

void usage(int argc, char* argv[]) {
    printf("Usage: %s <analyzer_folder> <output_folder> <link b/s> <rtt_d> <rtt_r>\n", argv[0]);
    exit(1);
}

void loadParameters(int argc, char **argv) {
    if (argc < 6) {
        usage(argc, argv);
    }

    params->analyzer_folder = argv[1];
    params->output_folder = argv[2];
    params->link = atoi(argv[3]);
    params->rtt_d = (double) atoi(argv[4]);
    params->rtt_r = (double) atoi(argv[5]);
}

int main(int argc, char **argv) {
    loadParameters(argc, argv);

    getSamplesQS();
    getSamplesRateMarksDrops();
    getSamplesUtilization();

    if (res->rate_nonecn->average() > 0) {
        res->rr_static = res->rate_ecn->average() / res->rate_nonecn->average();
        res->wr_static = res->win_ecn->average() / res->win_nonecn->average();
    }

    if (res->drops_qs_nonecn->p(99) > 100) {
        std::cerr << "too high drops p99: " << res->drops_qs_nonecn->p(99) << std::endl;
        exit(1);
    }

    writeStatistics("qs_ecn_stats", res->qs_ecn);
    writeStatistics("qs_nonecn_stats", res->qs_nonecn);
    //writeStatistics("r_tot_ecn_stats", res->rate_ecn);
    //writeStatistics("r_tot_nonecn_stats", res->rate_nonecn);
    //writeStatistics("win_ecn_stats", res->win_ecn);
    //writeStatistics("win_nonecn_stats", res->win_nonecn);
    writeStatistics("d_percent_ecn_stats", res->drops_qs_ecn);
    writeStatistics("d_percent_nonecn_stats", res->drops_qs_nonecn);
    writeStatistics("m_percent_ecn_stats", res->marks_ecn);
    writeStatistics("util_nonecn_stats", res->util_nonecn);
    writeStatistics("util_ecn_stats", res->util_ecn);
    writeStatistics("util_total_stats", res->util_total);

    //out << res->rr_static << std::endl;
    //writeToFile("rr", out.str()); out.str("");

    //out << res->wr_static << std::endl;
    //writeToFile("wr", out.str()); out.str("");

    return 0;
}
