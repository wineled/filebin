/*
 * 简单的测试程序，用于生成带 DWARF 调试信息的 ELF
 */
#include <stdio.h>

// ----------------- filler start (100 lines) -----------------
// 本段为自动插入的占位代码，位于 `add` 函数之前
// 插入目的是测试文件修改对 DWARF/构建流程的影响
// 请注意：这些行仅为注释，不影响程序行为

// filler line 100
// ----------------- filler end -----------------

/* 插入排序函数：约 100 行实现（自包含，稳定、基于自底向上的归并排序） */
#include <stdlib.h>

/*
 * sort_array
 *  对整数数组进行排序（升序）。
 *
 *  说明：本函数实现的是自底向上的归并排序（迭代版本），
 *  使用一次性分配的临时缓冲区，避免递归开销。
 *
 *  参数：
 *    arr - 指向待排序整数数组的指针
 *    n   - 数组元素个数
 */
void sort_array(int *arr, int n) {
    if (!arr || n <= 1) {
        return;
    }

    /* 申请临时缓冲区 */
    int *tmp = (int *)malloc((size_t)n * sizeof(int));
    if (!tmp) {
        /* 内存分配失败，退化为简单插入排序 */
        for (int i = 1; i < n; ++i) {
            int key = arr[i];
            int j = i - 1;
            while (j >= 0 && arr[j] > key) {
                arr[j + 1] = arr[j];
                --j;
            }
            arr[j + 1] = key;
        }
        return;
    }

    /* 自底向上的归并：宽度从 1,2,4,... 翻倍 */
    for (int width = 1; width < n; width <<= 1) {
        for (int left = 0; left < n; left += (width << 1)) {
            int mid = left + width;
            if (mid >= n) {
                /* 右侧为空，直接拷贝左侧 */
                continue;
            }
            int right = mid + width;
            if (right > n) right = n;

            /* i 指向左区间当前元素， j 指向右区间当前元素 */
            int i = left;
            int j = mid;
            int k = left;

            while (i < mid && j < right) {
                if (arr[i] <= arr[j]) {
                    tmp[k++] = arr[i++];
                } else {
                    tmp[k++] = arr[j++];
                }
            }

            /* 将剩余元素复制到 tmp */
            while (i < mid) tmp[k++] = arr[i++];
            while (j < right) tmp[k++] = arr[j++];

            /* 将 tmp 中已排序区间复制回 arr */
            for (k = left; k < right; ++k) {
                arr[k] = tmp[k];
            }
        }
    }

    free(tmp);
}

/* 示例辅助函数：打印数组（仅用于调试/验证，可安全保留） */
void print_array(const int *arr, int n) {
    if (!arr) return;
    for (int i = 0; i < n; ++i) {
        printf("%d", arr[i]);
        if (i + 1 < n) printf(", ");
    }
    printf("\n");
}

/* 原有函数保持不变 */
int add111(int a, int b) {
    int sum = a + b;
    int c =10;
    sum += c;
    printf("Adding111 %d and %d\n", a, b);
    return sum;
}

int add(int a, int b) {
    int sum = a + b;
    int c =10;
    sum += c;
    printf("Adding %d and %d\n", a, b);

    return sum;
}

int layer4(int a, int b) {
    printf("Calling layer4 with %d and %d\n", a, b);
    return add(a, b);
}

int layer3(int a, int b) {
    printf("Calling layer3 with %d and %d\n", a, b);            
    return layer4(a, b);
}

int layer2(int a, int b) {
    printf("Calling layer2 with %d and %d\n", a, b);
    return layer3(a, b);
}

int layer1(int a, int b) {
    printf("Calling layer1 with %d and %d\n", a, b);
    return layer2(a, b);
}

int main() {
    int result = layer3(10, 50);
    printf("Result: %d\n", result);
    add(20, 30);
    add111(5, 15);
    layer1(100, 200);
    return 0;
}