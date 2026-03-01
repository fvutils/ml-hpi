/* tb_dpi_test.c -- C-side DPI test driver for the C->SV path.
 *
 * DPI call sequence:
 *  1. SV calls ml_hpi_test_start(root_id)   [import -- C provides]
 *  2. C sets scope, calls tb_RegIf_write32(...)  [export -- SV provides]
 *     SV forks write task, returns immediately.
 *  3. SV write task completes, calls tb_RegIf_write32_complete(cb)
 *  4. C sets scope, calls tb_RegIf_read32(...)   [export -- SV provides]
 *  5. SV read task completes, calls tb_RegIf_read32_complete(cb, rval)
 *  6. C checks rval, sets tb_test scope, calls ml_hpi_test_finish() -> $finish
 */
#include <stdio.h>
#include <stdint.h>
#include "tb_RegIf_dpi.h"

/* All functions are called by Verilator's C++ wrapper, so they need C linkage. */
#ifdef __cplusplus
extern "C" {
#endif

/* Static scope handles captured at elaboration by the init functions */
static svScope s_tb_RegIf_dpi_scope;
static svScope s_tb_test_scope;

/* Implemented in tb_test_pkg.sv -- SV provides, C calls */
extern void ml_hpi_test_finish(void);

/* tb_RegIf_dpi package init: capture the package scope */
int tb_RegIf_dpi_init(void) {
    s_tb_RegIf_dpi_scope = svGetScope();
    return 0;
}

/* tb_RegIf_dpi scope setter — called before invoking any tb_RegIf_dpi export */
void tb_RegIf_dpi_set_scope(void) {
    svSetScope(s_tb_RegIf_dpi_scope);
}

/* tb_test package init: capture the test package scope */
int tb_test_init(void) {
    s_tb_test_scope = svGetScope();
    return 0;
}

static int g_root_id = -1;
static struct { int placeholder; } g_write_cb;
static struct { int placeholder; } g_read_cb;

void tb_RegIf_write32_complete(void *cb) {
    tb_RegIf_dpi_set_scope();
    tb_RegIf_read32(g_root_id, 0, 0x1000ULL, &g_read_cb);
}

void tb_RegIf_read32_complete(void *cb, uint32_t rval) {
    if (rval == 0xCAFEBABEU) {
        printf("RESULT: PASS rval=0x%08x\n", rval);
    } else {
        printf("RESULT: FAIL expected=0xcafebabe got=0x%08x\n", rval);
    }
    /* Switch to tb_test package scope to call ml_hpi_test_finish export */
    svSetScope(s_tb_test_scope);
    ml_hpi_test_finish();
}

void ml_hpi_test_start(int root_id) {
    g_root_id = root_id;
    printf("C:  test_start root_id=%d\n", root_id);
    tb_RegIf_dpi_set_scope();
    tb_RegIf_write32(g_root_id, 0, 0x1000ULL, 0xCAFEBABEU, &g_write_cb);
}

#ifdef __cplusplus
}
#endif
