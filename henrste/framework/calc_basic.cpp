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

#define MAX_QS 2048

#define percentile(p, n) (ceil(float(p)/100*float(n)))

struct Parameters {
    double rtt_d;
    double rtt_r;
    std::string folder;
    double link;
    int samples_to_skip;

    Parameters() {
        rtt_d = 0;
        rtt_r = 0;
        folder = "";
        link = 0;
        samples_to_skip = 0;
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
    Statistics *queue_ecn;
    Statistics *queue_nonecn;
    Statistics *drops_ecn;
    Statistics *drops_nonecn;
    Statistics *marks_ecn;
    Statistics *util_ecn;
    Statistics *util_nonecn;
    Statistics *util_total;

    double rr_static;
    double wr_static;

    double ecn_avg;
    double nonecn_avg;

    Results() {
        rate_ecn = new Statistics();
        rate_nonecn = new Statistics();
        win_ecn = new Statistics();
        win_nonecn = new Statistics();
        queue_ecn = new Statistics();
        queue_nonecn = new Statistics();
        drops_ecn = new Statistics();
        drops_nonecn = new Statistics();
        marks_ecn = new Statistics();
        util_ecn = new Statistics();
        util_nonecn = new Statistics();
        util_total = new Statistics();

        rr_static = NAN;
        wr_static = NAN;

        ecn_avg = NAN;
        nonecn_avg = NAN;
    }
};

struct Parameters *params = new Parameters();
struct Results *res = new Results();

void openFileR(std::ifstream *file, std::string filename) {
    *file = std::ifstream(filename.c_str());
    if (!file->is_open()) {
        std::cerr << "Error opening file for reading: " << filename << std::endl;
        exit(1);
    }
}

void openFileW(std::ofstream *file, std::string filename) {
    *file = std::ofstream(filename.c_str());
    if (!file->is_open()) {
        std::cerr << "Error opening file for writing: " << filename << std::endl;
        exit(1);
    }
}

void writeToFile(std::string filename, std::string data) {
    std::ofstream file;
    openFileW(&file, params->folder + "/" + filename);
    file << data;
    file.close();
}

void writeStatistics(std::string filename, Statistics *stats) {
    std::stringstream out;
    out << "# average stddev min p1 p25 p50 p75 p99 max" << std::endl;
    out << stats->average() << " " << stats->stddev() << " "
        << stats->front() << " "
        << stats->p(1) << " " << stats->p(25) << " " << stats->p(50) << " "
        << stats->p(75) << " " << stats->p(99) << " "
        << stats->back() << "" << std::endl;
    writeToFile(filename, out.str());
}

void readFileMarks(std::string filename_marks, Statistics *stats, std::string filename_tot) {
    std::ifstream infile_marks, infile_tot;
    openFileR(&infile_marks, filename_marks);
    openFileR(&infile_tot, filename_tot);

    std::vector<double> *samples = new std::vector<double>();

    // Columns in drops file we are reading:
    // <sample number> <sample time> <marks>

    // Columns in total packets file we are reading:
    // <number of packets>

    // skip samples we are not interested in
    std::string line;
    for (int i = 0; i < params->samples_to_skip; i++) {
        getline(infile_tot, line);
        getline(infile_marks, line);
    }

    while (1) {
        double marks;
        double tot_packets;
        double marks_perc = 0;

        infile_tot >> tot_packets;

        // skip first two cols
        infile_marks >> marks;
        infile_marks >> marks;
        infile_marks >> marks;

        if (infile_marks.eof() || infile_tot.eof()) {
            break;
        }

        if (tot_packets > 0) {
            marks_perc = marks * 100 / tot_packets;
        }

        samples->push_back(marks_perc);
    }

    infile_marks.close();
    infile_tot.close();
    stats->samples(samples);
}

void readFileDrops(std::string filename_drops, Statistics *stats, std::string filename_tot) {
    std::ifstream infile_drops, infile_tot;
    openFileR(&infile_drops, filename_drops);
    openFileR(&infile_tot, filename_tot);

    std::vector<double> *samples = new std::vector<double>();

    // Columns in drops file we are reading:
    // <sample number> <sample time> <drops>

    // Columns in total packets file we are reading:
    // <number of packets>

    // skip samples we are not interested in
    std::string line;
    for (int i = 0; i < params->samples_to_skip; i++) {
        getline(infile_tot, line);
        getline(infile_drops, line);
    }

    while (1) {
        double drops;
        double tot_packets;
        double drops_perc = 0;

        infile_tot >> tot_packets;

        // skip first two cols
        infile_drops >> drops;
        infile_drops >> drops;
        infile_drops >> drops;

        if (infile_drops.eof() || infile_tot.eof()) {
            break;
        }

        if (tot_packets + drops > 0) {
            drops_perc = drops * 100 / (tot_packets + drops);
        }

        samples->push_back(drops_perc);

        if (drops_perc > 100) {
            std::cout << "too large drops perc: " << drops_perc << std::endl;
        }
    }

    infile_drops.close();
    infile_tot.close();
    stats->samples(samples);
}

void readFileRate(std::string filename, Statistics *stats_rate, Statistics *stats_win, double avg_queue, double rtt) {
    std::ifstream infile;
    openFileR(&infile, filename);

    std::vector<double> *samples_rate = new std::vector<double>();
    std::vector<double> *samples_win = new std::vector<double>();

    // Columns in file we are reading:
    // <sample number> <sample time> <rate b/s>

    // skip samples we are not interested in
    std::string line;
    for (int i = 0; i < params->samples_to_skip; i++) {
        getline(infile, line);
    }

    /* avg_queue is in us, rtt is in ms - add them and convert to s */
    double rtt_with_queue_in_s = (avg_queue / 1000 + rtt) / 1000

    while (1) {
        double rate;
        double win = 0;

        std::string line;
        getline(infile, line);

        std::istringstream iss(line);

        // skip first two cols
        iss >> rate;
        iss >> rate;
        iss >> rate;

        if (infile.eof()) {
            break;
        }

        if (avg_queue != 0) {
            /* window is in bits, not packets as we don't know packet size! */
            win = rate * rtt_with_queue_in_s;
        }

        samples_rate->push_back(rate);
        samples_win->push_back(win);
    }

    infile.close();
    stats_rate->samples(samples_rate);
    stats_win->samples(samples_win);
}

void getSamplesUtilization() {
    std::string filename_ecn = params->folder + "/ta/rate_ecn";
    std::string filename_nonecn = params->folder + "/ta/rate_nonecn";

    std::ifstream infile_ecn, infile_nonecn;
    openFileR(&infile_ecn, filename_ecn);
    openFileR(&infile_nonecn, filename_nonecn);

    std::vector<double> *samples_ecn = new std::vector<double>();
    std::vector<double> *samples_nonecn = new std::vector<double>();
    std::vector<double> *samples_total = new std::vector<double>();

    // Columns in file we are reading:
    // <sample number> <sample time> <rate b/s>

    // skip samples we are not interested in
    std::string line;
    for (int i = 0; i < params->samples_to_skip; i++) {
        getline(infile_ecn, line);
        getline(infile_nonecn, line);
    }

    while (1) {
        double rate_ecn;
        double rate_nonecn;
        double util_ecn;
        double util_nonecn;
        double util_total;

        // skip first two cols
        infile_ecn >> rate_ecn;
        infile_ecn >> rate_ecn;
        infile_ecn >> rate_ecn;
        infile_nonecn >> rate_nonecn;
        infile_nonecn >> rate_nonecn;
        infile_nonecn >> rate_nonecn;

        if (infile_ecn.eof() || infile_nonecn.eof()) {
            break;
        }

        util_ecn = rate_ecn * 100 / params->link;
        util_nonecn = rate_nonecn * 100 / params->link;
        util_total = (rate_ecn+rate_nonecn) * 100 / params->link;

        samples_ecn->push_back(util_ecn);
        samples_nonecn->push_back(util_nonecn);
        samples_total->push_back(util_total);
    }

    infile_ecn.close();
    infile_nonecn.close();

    res->util_ecn->samples(samples_ecn);
    res->util_nonecn->samples(samples_nonecn);
    res->util_total->samples(samples_total);
}

void readFileQS(std::string filename, Statistics *stats) {
    std::ifstream infile;
    openFileR(&infile, filename);

    std::vector<double> *samples = new std::vector<double>();

    // Columns in file we are reading:
    // <queuing delay in us> <number of packes not dropped> <number of packets dropped>

    // we don't skip any samples for this one, as the input data
    // is already aggregated over all samples

    while (1) {
        double us;
        double nrpackets;
        double drops;

        infile >> us; /* number of us each packet represents */
        infile >> nrpackets;
        infile >> drops;

        if (infile.eof()) {
            break;
        }

        for (int i = 0; i < nrpackets; ++i) {
            samples->push_back(us);
        }
    }

    infile.close();

    stats->samples(samples);
}

void getSamplesRateMarksDrops() {
    readFileRate(params->folder + "/ta/rate_ecn", res->rate_ecn, res->win_ecn, res->queue_ecn->average(), params->rtt_d);
    readFileMarks(params->folder + "/ta/marks_ecn", res->marks_ecn, params->folder + "/ta/packets_ecn");
    readFileDrops(params->folder + "/ta/drops_ecn", res->drops_ecn, params->folder + "/ta/packets_ecn");
    readFileRate(params->folder + "/ta/rate_nonecn", res->rate_nonecn, res->win_nonecn, res->queue_nonecn->average(), params->rtt_r);
    readFileDrops(params->folder + "/ta/drops_nonecn", res->drops_nonecn, params->folder + "/ta/packets_nonecn");
}

void getSamplesQS() {
    readFileQS(params->folder + "/aggregated/queue_packets_drops_ecn_pdf", res->queue_ecn);
    readFileQS(params->folder + "/aggregated/queue_packets_drops_nonecn_pdf", res->queue_nonecn);
}

void usage(int argc, char* argv[]) {
    printf("Usage: %s <test_folder> <link b/s> <rtt_d> <rtt_r> <samples_to_skip>\n", argv[0]);
    exit(1);
}

void loadParameters(int argc, char **argv) {
    if (argc < 6) {
        usage(argc, argv);
    }

    params->folder = argv[1];
    params->link = atoi(argv[2]);
    params->rtt_d = (double) atoi(argv[3]);
    params->rtt_r = (double) atoi(argv[4]);
    params->samples_to_skip = atoi(argv[5]);
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

    if (res->drops_nonecn->p(99) > 100) {
        std::cerr << "too high drops p99: " << res->drops_nonecn->p(99) << std::endl;
        exit(1);
    }

    writeStatistics("aggregated/queue_ecn_stats", res->queue_ecn);
    writeStatistics("aggregated/queue_nonecn_stats", res->queue_nonecn);
    //writeStatistics("aggregated/rate_ecn_stats", res->rate_ecn);
    //writeStatistics("aggregated/rate_nonecn_stats", res->rate_nonecn);
    //writeStatistics("aggregated/win_ecn_stats", res->win_ecn);
    //writeStatistics("aggregated/win_nonecn_stats", res->win_nonecn);
    writeStatistics("aggregated/drops_percent_ecn_stats", res->drops_ecn);
    writeStatistics("aggregated/drops_percent_nonecn_stats", res->drops_nonecn);
    writeStatistics("aggregated/marks_percent_ecn_stats", res->marks_ecn);
    writeStatistics("aggregated/util_nonecn_stats", res->util_nonecn);
    writeStatistics("aggregated/util_ecn_stats", res->util_ecn);
    writeStatistics("aggregated/util_stats", res->util_total);

    std::stringstream out;

    out << res->rr_static << std::endl;
    writeToFile("aggregated/ecn_over_nonecn_rate_ratio", out.str()); out.str("");

    out << res->wr_static << std::endl;
    writeToFile("aggregated/ecn_over_nonecn_window_ratio", out.str()); out.str("");

    return 0;
}
