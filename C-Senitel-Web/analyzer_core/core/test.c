//
// Created by RAJ ADITYA on 15-10-2025.
//
#include <stdio.h>
void main() {
    char name[2048];
    printf("Enter your name: ");
    scanf("%[^\n]s", name);                                             
    int *roll_no;
    printf("Enter your roll number: ");
    scanf("%d", &roll_no);
    printf(name);
    printf(roll_no);

    int a[10];
    a[2] = a[1] + 3;
    foo(a[2], x->field, obj.field);
    x->field++;
    f(g(h(1)), a[ b[2] ], obj->m1.m2);
}