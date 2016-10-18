#include "analysis.h"

#include <stdio.h>
#include <stdlib.h>
#include <iostream>
#include <string>

void usage(int argc, char* argv[])
{
    printf("Usage: %s <dev> <pcap filter exp> <output folder> <sample interval (ms)> (optional:) <ip classification> <nrsamples>\n", argv[0]);
    printf("pcap filter: what to capture. ex.: \"ip and src net 10.187.255.0/24\"\n");
    printf("If nrsamples is not specified, the samples will be recorded until interrupted\nIp classification is t/f (default f); the 2 lsbits of the src ip are used.\n");
    exit(1);
}

int main(int argc, char **argv)
{
    char *dev;
    char *folder;
    uint32_t sinterval;
    uint32_t nrs = 0;
    bool ipclass = false;

    if (argc < 5)
        usage(argc, argv);

    dev = argv[1];

    folder = argv[3];
    sinterval = atoi(argv[4]);
    std::string pcapfilter = argv[2];

    std::cout << "pcap filter: " << pcapfilter << std::endl;

    if (argc > 5)
        ipclass = (argv[5][0] == 't');

    if (argc > 6)
        nrs = atoi(argv[6]);

    start_analysis(dev, folder, sinterval, pcapfilter, ipclass, nrs, 0);

    //fprintf(stderr,"main exiting..\n");
    return 0;
}
