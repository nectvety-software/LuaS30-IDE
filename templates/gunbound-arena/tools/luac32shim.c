#include <windows.h>
#include <stdio.h>
#include <string.h>

#define LUAC "C:\\Users\\doxuanhop\\Documents\\LuaS30 Projects\\VXP_Pixel_Editor\\tools\\luac51\\luac.exe"
#define PY   "C:\\Users\\doxuanhop\\.platformio\\python3\\python.exe"
#define CONV "C:\\Users\\doxuanhop\\Documents\\LuaS30 Projects\\gunbound-arena\\tools\\lua_ilp32.py"

static int run(const char *exe, char **args, int nargs) {
    static char cmd[16384];
    int p;
    DWORD ec;
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;
    p = _snprintf(cmd, sizeof(cmd), "\"%s\"", exe);
    if (p < 0 || p >= (int)sizeof(cmd)) return -1;
    for (int i = 0; i < nargs; i++) {
        p += _snprintf(cmd + p, sizeof(cmd) - p, " \"%s\"", args[i]);
        if (p < 0 || p >= (int)sizeof(cmd)) return -1;
    }
    memset(&si, 0, sizeof si);
    si.cb = sizeof si;
    if (!CreateProcessA(NULL, cmd, NULL, NULL, TRUE, 0, NULL, NULL, &si, &pi)) {
        fprintf(stderr, "luac32shim: cannot start: %s (err %lu)\n", cmd, GetLastError());
        return -1;
    }
    WaitForSingleObject(pi.hProcess, INFINITE);
    GetExitCodeProcess(pi.hProcess, &ec);
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    return (int)ec;
}

int main(int argc, char **argv) {
    const char *dst = NULL;
    int rc;
    char *conv_args[2];
    for (int i = 1; i < argc; i++)
        if (strcmp(argv[i], "-o") == 0 && i + 1 < argc) dst = argv[++i];
    rc = run(LUAC, argv + 1, argc - 1);
    if (rc) return rc;
    if (!dst) {
        fprintf(stderr, "luac32shim: no -o output to convert\n");
        return 2;
    }
    conv_args[0] = (char *)CONV;
    conv_args[1] = (char *)dst;
    rc = run(PY, conv_args, 2);
    if (rc) fprintf(stderr, "luac32shim: conversion failed rc=%d for %s\n", rc, dst);
    return rc;
}
