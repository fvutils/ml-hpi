/* tb_dpi_test.c — C-side DPI test driver for the C→SV path.
 *
 * DPI call sequence:
 *  1. SV calls ml_hpi_test_start(root_id)   [import — C provides]
 *  2. C calls tb_RegIf_write32(...)          [export — SV provides]
 *     SV forks write task, returns immediately.
 *  3. SV write task completes, calls tb_RegIf_write32_complete(cb) [import — C provides]
 *  4. C calls tb_RegIf_read32(...)           [export — SV provides]
 *     SV forks read task, returns immediately.
 *  5. SV read task completes, calls tb_RegIf_read32_complete(cb, rval) [import — C provides]
 *  6. C checks rval, calls ml_hpi_test_finish() [export — SV provides] → $finish
 */
#include <stdio.h>
#include <stdint.h>
#include "tb_RegIf_dpi.h"

/* DPI export provided by SV tb_top */
extern void ml_hpi_test_finish(void);

static int g_root_id = -1;

/* Dummy pending structs — the cb pointer is not dereferenced by SV;
 * we use static storage so it remains valid after each function returns. */
static struct { int placeholder; } g_write_cb;
static struct { int placeholder; } g_read_cb;

/* -----------------------------------------------------------------------
 * Completion callbacks — C provides, SV calls when forked tasks finish
 * ----------------------------------------------------------------------- */

void tb_RegIf_write32_complete(void *cb) {
    /* Write done — issue the read */
    tb_RegIf_read32(g_root_id, /*path=root*/ 0, /*addr*/ 0x1000ULL, &g_read_cb);
}

void tb_RegIf_read32_complete(void *cb, uint32_t rval) {
    if (rval == 0xCAFEBABEU) {
        printf("RESULT: PASS rval=0x%08x\n", rval);
    } else {
        printf("RESULT: FAIL expected=0xcafebabe got=0x%08x\n", rval);
    }
    ml_hpi_test_finish();   /* tell SV to $finish */
}

/* -----------------------------------------------------------------------
 * Test entry point — SV calls this after registering its root instance
 * ----------------------------------------------------------------------- */
void ml_hpi_test_start(int root_id) {
    g_root_id = root_id;
    printf("C:  test_start root_id=%d\n", root_id);
    /* Issue write32 to the root RegIf at path=0 */
    tb_RegIf_write32(g_root_id, /*path=root*/ 0,
                     /*addr*/ 0x1000ULL, /*data*/ 0xCAFEBABEU, &g_write_cb);
}
