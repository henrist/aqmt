#include <fstream>
#include <string>
#include <vector>
#include <iostream>

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

void readFile(std::string filename, std::vector<uint64_t> **header,
    std::vector<uint64_t> **values, int samples_to_skip)
{
    std::ifstream infile;
    openFileR(&infile, filename);

    // Format of file:
    // Header row: <number of columns> <value 1 header> <value 2 header> ...
    // Each following row is a sample: <sample time> <value 1> <value 2> ...

    // Read header
    int column_count = 0;
    infile >> column_count;

    if (header != NULL) {
        *header = new std::vector<uint64_t>();
    }

    for (int i = 0; i < column_count; i++) {
        uint64_t value;
        infile >> value;
        if (header != NULL) {
            (*header)->push_back(value);
        }
    }

    // Skip samples we are not interested in
    std::string line;
    for (int i = 0; i < samples_to_skip; i++) {
        getline(infile, line);
    }

    // Read samples and aggregate the rows
    if (*values == NULL) {
        *values = new std::vector<uint64_t>(column_count, 0);
    }

    while (1) {
        uint64_t value;

        // Skip first col
        infile >> value;

        if (infile.eof()) {
            break;
        }

        for (int i = 0; i < column_count; i++) {
            infile >> value;
            (*values)->at(i) += value;
        }
    }
}

void writePdfCdf(std::string filename_pdf, std::string filename_cdf, std::vector<uint64_t> *header, std::vector<uint64_t> *sent, std::vector<uint64_t> *drops) {
    std::ofstream f_pdf, f_cdf;
    openFileW(&f_pdf, filename_pdf);
    openFileW(&f_cdf, filename_cdf);

    // Columns in the output:
    // (one row for each queue delay)
    // <queue delay> <number of packets sent> <number of packets dropped>

    uint64_t sent_cdf = 0;
    uint64_t drops_cdf = 0;

    auto it_header = begin(*header);
    auto it_sent = begin(*sent);
    auto it_drops = begin(*drops);

    printf("val: %lu\n", *it_sent);

    while (it_header != end(*header)) {
        sent_cdf += *it_sent;
        drops_cdf += *it_drops;

        f_pdf << *it_header << " " << *it_sent << " " << *it_drops << std::endl;
        f_cdf << *it_header << " " << sent_cdf << " " << drops_cdf << std::endl;

        it_header++;
        it_sent++;
        it_drops++;
    }

    f_pdf.close();
    f_cdf.close();
}

void usage(int argc, char* argv[]) {
    printf("Usage: %s <test_folder> <samples_to_skip>\n", argv[0]);
    exit(1);
}

int main(int argc, char **argv) {
    if (argc < 3) {
        usage(argc, argv);
    }

    std::string folder = argv[1];
    int samples_to_skip = atoi(argv[2]);

    std::vector<uint64_t> *header = NULL;
    std::vector<uint64_t> *values_qd_classic = NULL;
    std::vector<uint64_t> *values_qd_l4s = NULL;
    std::vector<uint64_t> *values_d_classic = NULL;
    std::vector<uint64_t> *values_d_l4s = NULL;

    readFile(folder + "/ta/queue_packets_ecn00", &header, &values_qd_classic, samples_to_skip);
    readFile(folder + "/ta/queue_packets_ecn01", NULL, &values_qd_l4s, samples_to_skip);
    readFile(folder + "/ta/queue_packets_ecn10", NULL, &values_qd_l4s, samples_to_skip);
    readFile(folder + "/ta/queue_packets_ecn11", NULL, &values_qd_l4s, samples_to_skip);

    readFile(folder + "/ta/queue_drops_ecn00", NULL, &values_d_classic, samples_to_skip);
    readFile(folder + "/ta/queue_drops_ecn01", NULL, &values_d_l4s, samples_to_skip);
    readFile(folder + "/ta/queue_drops_ecn10", NULL, &values_d_l4s, samples_to_skip);
    readFile(folder + "/ta/queue_drops_ecn11", NULL, &values_d_l4s, samples_to_skip);

    writePdfCdf(
        folder + "/aggregated/queue_packets_drops_nonecn_pdf",
        folder + "/aggregated/queue_packets_drops_nonecn_cdf",
        header,
        values_qd_classic,
        values_d_classic
    );

    writePdfCdf(
        folder + "/aggregated/queue_packets_drops_ecn_pdf",
        folder + "/aggregated/queue_packets_drops_ecn_cdf",
        header,
        values_qd_l4s,
        values_d_l4s
    );
}
