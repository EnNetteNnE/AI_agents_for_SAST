// minimal_cpp/test.cpp
#include <stdio.h>
#include <string.h>

int main() {
    char buffer[100];
    strcpy(buffer, "hello");  // классический overflow
    printf("%s\\n", buffer);
    
    int* ptr = new int(42);
    delete ptr;
    *ptr = 0;  // use-after-free
    
    return 0;
}

