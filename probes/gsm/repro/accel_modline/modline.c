// The two versions of accel_verilog_module's header scan (nvc/src/rt/model.c),
// lifted verbatim into a standalone program so the difference can be shown
// without an nvc rebuild:  ./modline <file.v> <line>
//   old: counts fgets() chunks (4096-byte buffer) as lines; no lifetime keywords
//   new: counts physical lines; skips `automatic` / `static`
#include <ctype.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static bool scan_old(const char *path, int line, char *out, size_t outsz)
{
   FILE *f = fopen(path, "r");
   if (f == NULL)
      return false;
   bool found = false;
   char buf[4096];
   for (int ln = 1; !found && ln <= line + 3 && fgets(buf, sizeof buf, f); ln++) {
      if (ln < line)
         continue;
      for (const char *p = strstr(buf, "module"); p != NULL;
           p = strstr(p + 6, "module")) {
         const bool kw = (p == buf || !(isalnum((unsigned char)p[-1])
                                        || p[-1] == '_'))
            && isspace((unsigned char)p[6]);
         if (!kw)
            continue;
         p += 6;
         while (isspace((unsigned char)*p))
            p++;
         size_t n = 0;
         for (; n + 1 < outsz && (isalnum((unsigned char)p[n]) || p[n] == '_'
                                  || p[n] == '$'); n++)
            out[n] = p[n];
         out[n] = '\0';
         found = n > 0;
         break;
      }
   }
   fclose(f);
   return found;
}

static bool scan_new(const char *path, int line, char *out, size_t outsz)
{
   FILE *f = fopen(path, "r");
   if (f == NULL)
      return false;
   bool found = false;
   char buf[4096];
   int ln = 1;
   while (!found && ln <= line + 3 && fgets(buf, sizeof buf, f)) {
      const size_t len = strlen(buf);
      const bool eol = len > 0 && buf[len - 1] == '\n';
      if (ln < line) {
         if (eol) ln++;
         continue;
      }
      for (const char *p = strstr(buf, "module"); p != NULL;
           p = strstr(p + 6, "module")) {
         const bool kw = (p == buf || !(isalnum((unsigned char)p[-1])
                                        || p[-1] == '_'))
            && isspace((unsigned char)p[6]);
         if (!kw)
            continue;
         p += 6;
         while (isspace((unsigned char)*p))
            p++;
         static const char *const lifetime[] = { "automatic", "static" };
         for (size_t k = 0; k < sizeof lifetime / sizeof lifetime[0]; k++) {
            const size_t l = strlen(lifetime[k]);
            if (strncmp(p, lifetime[k], l) == 0
                && isspace((unsigned char)p[l])) {
               p += l;
               while (isspace((unsigned char)*p))
                  p++;
            }
         }
         size_t n = 0;
         for (; n + 1 < outsz && (isalnum((unsigned char)p[n]) || p[n] == '_'
                                  || p[n] == '$'); n++)
            out[n] = p[n];
         out[n] = '\0';
         found = n > 0;
         break;
      }
      if (eol) ln++;
   }
   fclose(f);
   return found;
}

int main(int argc, char **argv)
{
   if (argc != 3) {
      fprintf(stderr, "usage: %s <file.v> <module line>\n", argv[0]);
      return 2;
   }
   const int line = atoi(argv[2]);
   char o[320];
   printf("old scanner: %s\n", scan_old(argv[1], line, o, sizeof o) ? o : "(not found)");
   printf("new scanner: %s\n", scan_new(argv[1], line, o, sizeof o) ? o : "(not found)");
   return 0;
}
