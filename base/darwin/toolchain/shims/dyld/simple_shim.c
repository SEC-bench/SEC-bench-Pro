/* Implementation of the <_simple.h> shim.  See shims/_simple.h. */
#include "_simple.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct simple_buf {
    char  *buf;
    size_t cap;
    size_t used;   /* strlen(buf) */
};

static struct simple_buf *sb(void *p) { return (struct simple_buf *)p; }

_SIMPLE_STRING _simple_salloc(void)
{
    struct simple_buf *b = (struct simple_buf *)calloc(1, sizeof(*b));
    if ( b == NULL )
        return NULL;
    b->cap = 256;
    b->buf = (char *)malloc(b->cap);
    if ( b->buf == NULL ) { free(b); return NULL; }
    b->buf[0] = '\0';
    return b;
}

void _simple_sfree(_SIMPLE_STRING p)
{
    if ( p == NULL )
        return;
    free(sb(p)->buf);
    free(sb(p));
}

char *_simple_string(_SIMPLE_STRING p)
{
    return (p == NULL) ? (char *)"" : sb(p)->buf;
}

/* Apple's semantics: move the insertion point to the end of the current
   string, so the next _simple_vsprintf appends instead of overwriting. */
void _simple_sresize(_SIMPLE_STRING p)
{
    if ( p != NULL )
        sb(p)->used = strlen(sb(p)->buf);
}

int _simple_vsprintf(_SIMPLE_STRING p, const char *fmt, va_list ap)
{
    struct simple_buf *b = sb(p);
    va_list ap2;
    int need;

    if ( b == NULL )
        return -1;
    va_copy(ap2, ap);
    need = vsnprintf(NULL, 0, fmt, ap2);
    va_end(ap2);
    if ( need < 0 )
        return -1;
    if ( b->used + (size_t)need + 1 > b->cap ) {
        size_t ncap = b->cap;
        char  *nbuf;
        while ( b->used + (size_t)need + 1 > ncap )
            ncap *= 2;
        nbuf = (char *)realloc(b->buf, ncap);
        if ( nbuf == NULL )
            return -1;
        b->buf = nbuf;
        b->cap = ncap;
    }
    vsnprintf(b->buf + b->used, b->cap - b->used, fmt, ap);
    b->used += (size_t)need;
    return need;
}

int _simple_sprintf(_SIMPLE_STRING p, const char *fmt, ...)
{
    va_list ap;
    int r;
    va_start(ap, fmt);
    r = _simple_vsprintf(p, fmt, ap);
    va_end(ap);
    return r;
}

int _simple_sappend(_SIMPLE_STRING p, const char *str)
{
    return _simple_sprintf(p, "%s", str);
}

/* dyld's apple[] array is "key=value" strings; return the value or NULL. */
const char *_simple_getenv(const char *envp[], const char *var)
{
    size_t len;
    if ( envp == NULL || var == NULL )
        return NULL;
    len = strlen(var);
    for ( const char **p = envp; *p != NULL; ++p ) {
        if ( strncmp(*p, var, len) == 0 && (*p)[len] == '=' )
            return *p + len + 1;
    }
    return NULL;
}

int _simple_vsnprintf(char *buf, size_t len, const char *fmt, va_list ap)
{
    return vsnprintf(buf, len, fmt, ap);
}

int _simple_snprintf(char *buf, size_t len, const char *fmt, ...)
{
    va_list ap;
    int r;
    va_start(ap, fmt);
    r = vsnprintf(buf, len, fmt, ap);
    va_end(ap);
    return r;
}
