#include <stdio.h>

int main(int argc, char** argv) {
    if (argc != 3) {
        printf("Invalid usage");
        return 1;
    }

    FILE* input = fopen(argv[1], "r");
    FILE* output = fopen(argv[3], "w");
    char buff[512];
    
    while(1){}

    return 0;
}