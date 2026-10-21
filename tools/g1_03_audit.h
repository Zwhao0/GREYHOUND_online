/* Original G1-03 instrumentation for the isolated NCCL example only.
 * No I/O/locks/allocation in callback additions; counters are relaxed atomics.
 * Include after event.h and the example's process-global startTime/pid.
 */
#include <stdint.h>
#include <stdlib.h>
#include <math.h>
static uint64_t g103_origin_ns;
static char g103_time_ns[80], g103_pid_ns[80], g103_boot_id[80];
static uint64_t g103_resolution_ns;
static uint64_t g103_now(void) {
  struct timespec t;
  if (clock_gettime(CLOCK_MONOTONIC, &t)) return 0;
  return (uint64_t)t.tv_sec * 1000000000ull + t.tv_nsec;
}
static void g103_link(const char* path, char* out, size_t size) {
  ssize_t n = readlink(path, out, size-1);
  if (n < 0) strcpy(out, "UNKNOWN"); else out[n] = 0;
}
static void g103_origin(void) {
  struct timespec t, r;
  if (clock_gettime(CLOCK_MONOTONIC, &t)) { g103_origin_ns = 0; return; }
  g103_origin_ns = (uint64_t)t.tv_sec * 1000000000ull + t.tv_nsec;
  startTime = t.tv_sec*1e6 + t.tv_nsec*1e-3;
  if (!clock_getres(CLOCK_MONOTONIC, &r))
    g103_resolution_ns = (uint64_t)r.tv_sec*1000000000ull+r.tv_nsec;
  g103_link("/proc/self/ns/time", g103_time_ns, sizeof(g103_time_ns));
  g103_link("/proc/self/ns/pid", g103_pid_ns, sizeof(g103_pid_ns));
  FILE* f = fopen("/proc/sys/kernel/random/boot_id", "r");
  if (!f || !fgets(g103_boot_id, sizeof(g103_boot_id), f)) strcpy(g103_boot_id,"UNKNOWN");
  if (f) fclose(f);
  g103_boot_id[strcspn(g103_boot_id,"\r\n")] = 0;
}
static void g103_add(struct context* c, int cls, int field) {
  __atomic_fetch_add(&c->g103[cls][field], 1, __ATOMIC_RELAXED);
}
__hidden void g103_export(struct context* c, int cls) { g103_add(c, cls, 5); }
static const char* g103_env(const char* name) {
  const char* s = getenv(name);
  if (!s || !*s) return "UNKNOWN";
  for (const char* p=s; *p; ++p)
    if (!( (*p>='a'&&*p<='z') || (*p>='A'&&*p<='Z') || (*p>='0'&&*p<='9') || *p=='_' || *p=='-' )) return "UNKNOWN";
  return s;
}
static void g103_audit(struct context* c, int opened, int wrote, int closed) {
  const char* dump = getenv("NCCL_PROFILE_DUMP_FILE");
  if (!dump) return;
  char path[PATH_MAX];
  if (snprintf(path,sizeof(path),"%s_%lu_%d.audit.json",dump,c->commHash,c->rank) >= sizeof(path)) return;
  FILE* f = fopen(path,"w");
  if (!f) return; /* Missing sidecar is UNKNOWN to the offline reader. */
  uint64_t finish = g103_now();
  /* A deliberately loose numerical bound for the example double-us conversion:
   * supported absolute monotonic range <2^42 us; each rounding <1 us.
   * It bounds representation only, not hardware accuracy or cross-node offset. */
  uint64_t rounding = (g103_origin_ns/1000ull < (1ull<<42) && finish/1000ull < (1ull<<42)) ? 4000 : 0;
  fprintf(f,"{\"schema_version\":1,\"run_id\":\"%s\",\"rank_epoch\":\"%s\",\"node_alias\":\"%s\",\"pid\":%d,\"comm_rank\":%d,\"comm_hash\":%lu,",g103_env("G103_RUN_ID"),g103_env("G103_EPOCH"),g103_env("G103_NODE"),getpid(),c->rank,c->commHash);
  fprintf(f,"\"origin_monotonic_ns\":%lu,\"active_until_monotonic_ns\":%lu,\"origin_mapping_error_ns\":%lu,\"resolution_ns\":%lu,\"clock_api\":\"clock_gettime(CLOCK_MONOTONIC)\",\"time_namespace\":\"%s\",\"pid_namespace\":\"%s\",\"boot_id\":\"%s\",",g103_origin_ns,finish,rounding,g103_resolution_ns,g103_time_ns,g103_pid_ns,g103_boot_id);
  fprintf(f,"\"export\":{\"file_open_ok\":%s,\"write_ok\":%s,\"close_ok\":%s,\"status\":\"%s\",\"durability\":\"UNKNOWN_NO_FSYNC\"},\"classes\":{",opened?"true":"false",wrote?"true":"false",closed?"true":"false",opened&&wrote&&closed?"OBSERVED":"UNKNOWN");
  const char* names[] = {"Group","Coll","KernelCh"};
  for(int i=0;i<3;i++) {
    uint64_t v[6]; for(int j=0;j<6;j++) v[j]=__atomic_load_n(&c->g103[i][j],__ATOMIC_RELAXED);
    fprintf(f,"%s\"%s\":{\"callback_attempted\":%lu,\"pool_accepted\":%lu,\"known_pool_drop\":%lu,\"parent_rejected\":%lu,\"guard_rejected\":%lu,\"overwritten\":\"UNKNOWN\",\"exported\":",i?",":"",names[i],v[0],v[1],v[2],v[3],v[4]);
    if(opened&&wrote&&closed) fprintf(f,"%lu",v[5]); else fprintf(f,"\"UNKNOWN\"");
    fprintf(f,",\"flush\":\"%s\",\"unit_scope\":\"start_callback_handle\",\"source\":\"G1-03 pinned example atomic counters; exported headers only; KernelCh accepted=embedded handle, no independent pool; upstream GPU timer ring overwrite UNKNOWN\"}",opened&&wrote&&closed?"OBSERVED_SUCCESS":"UNKNOWN");
  }
  fprintf(f,"},\"gpu_timer_ring_overwrite\":\"UNKNOWN\",\"callback_attempted_is_nccl_total\":false}\n");
  if (fflush(f) || ferror(f)) { /* Reader still rejects missing/malformed audit. */ }
  fclose(f);
}
