/*
 * 简单的测试程序，用于生成带 DWARF 调试信息的 ELF
 */
#include <stdio.h>

int add(int a, int b) {
    return a + b;
}

int layer4(int a, int b) {
    return add(a, b);
}

int layer3(int a, int b) {
    return layer4(a, b);
}

int layer2(int a, int b) {
    return layer3(a, b);
}

int layer1(int a, int b) {
    return layer2(a, b);
}

int main() {
    int result = layer1(10, 40);
    printf("Result: %d\n", result);
    return 0;
}