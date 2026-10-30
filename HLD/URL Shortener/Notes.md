# URL Shortener — HLD Notes

## 1. Traffic Estimation

**Chain:** Monthly volume → Average QPS → Peak QPS → Component sizing

```
Average QPS = Monthly count / (30 × 24 × 60 × 60)  [≈ monthly count / 2.6M]
Peak QPS    = Average QPS × peak multiplier (commonly ~2x for a typical
              consumer app's daily traffic curve)
```

- The multiplier is a stated assumption, not a fixed law. A service with viral/spiky
  traffic (like URL redirects after a link goes viral) may need a much higher multiplier
  for reads specifically — say so out loud rather than applying 2x blindly.
- **Never size components off average QPS.** Average is for cost estimation; peak is for
  capacity planning. Sizing off average leaves you under-provisioned exactly when it
  matters most.

### Numbers used in this exercise

| | Medium | Very High |
|---|---|---|
| Writes/month | 100M | 1B |
| Reads/month | 1B | 100B |
| Avg write QPS | ~38 | ~385 |
| Avg read QPS | ~385 | ~38,580 |
| Peak write QPS (×2) | ~77 | ~770 |
| Peak read QPS (×2) | ~770 | ~77,000 |

## 2. Formulas — Quick Reference

```
Average QPS = Monthly count / 2,592,000        (30 × 24 × 60 × 60 seconds/month)

Peak QPS = Average QPS × peak multiplier        (commonly ~2x; state it as an assumption)

────────────────────────────────────────────────────────────────
App Servers   = (Peak Read QPS + Peak Write QPS) / per-server capacity
                → rounded up
                e.g. (77,000 + 770) / 500 ≈ 155.5 → 156

Redis nodes   = (Peak Read QPS × cache hit rate) / per-node capacity
                → rounded up, then +N nodes for availability (not load)
                e.g. (77,000 × 0.9) / 100,000 ≈ 0.7 → 1 (+ 2–3 replicas for failover)

DB Replicas   = (Peak Read QPS × (1 − cache hit rate)) / per-instance capacity
                → rounded up
                e.g. (77,000 × 0.1) / 1,000 = 7.7 → 8

DB Master     = Peak Write QPS / per-instance write capacity
                → stays at 1 as long as possible; escalate via vertical scaling →
                  sharding (consistent hashing) → multi-master, in that order
                e.g. 770 / (large write ceiling) → 1

Load Balancers = (Peak Read QPS + Peak Write QPS) / per-LB capacity
                → rounded up, then treat as a floor — real count is usually
                  driven by availability (≥2), not this number
                e.g. 77,770 / 50,000 ≈ 1.56 → 2 (throughput minimum),
                  +1 more optionally for rolling-deploy headroom
────────────────────────────────────────────────────────────────
```

**Every count follows the same shape:**
```
Count = (load that reaches this component) / (what one instance can handle)
        → round UP, never down → add headroom for failover where relevant
```

The only thing that changes per component is the numerator — what load *actually*
reaches it after upstream filtering (see §2 below for why each one differs).

## 3. The Universal Sizing Pattern

For **any** component, in any system:

1. **What load actually reaches it?** (filtered by whatever sits upstream — not raw total traffic)
2. **What can one instance handle?** (a stated assumption, not a memorized constant)
3. **Count = load / capacity, round up, add headroom**

This is generic — it applies to app servers, Redis, DB replicas, Kafka partitions, anything.
What changes each time is step 1: correctly figuring out what load *actually* reaches that
specific component.

### Applied per component

| Component | Load that reaches it | Scales because of |
|---|---|---|
| App Servers | Full incoming traffic (reads + writes combined) — nothing upstream filters it | **Load** |
| Redis (cache) | Peak Read QPS × cache hit rate (the hits, not the misses) | **Load** (mostly) |
| DB Replicas | Peak Read QPS × (1 − hit rate) (the misses only) | **Load** |
| DB Master | Peak Write QPS (unfiltered — nothing absorbs writes before Master) | **Load**, but kept at 1 as long as possible |
| Load Balancer | N/A — nothing upstream of it to filter | **Availability**, not load |

**Key distinction:** some components scale because of *load* (app servers, replicas), others
because of *availability*, independent of load (load balancer, often extra Redis/replica nodes
even when under capacity). Don't justify one with the other.

## 3. Cache Hit Rate

- **Not calculated — assumed and stated.** You have no way to derive it from monthly traffic
  alone; it depends on real-world popularity distribution.
- URL shorteners have heavy **Zipf skew** (a small number of links get most of the traffic) →
  reasonable assumption: 90–95% hit rate.
- State it explicitly as an assumption in an interview, not as a fact.

## 4. Redis

- Runs in RAM vs. DB's disk → per-instance ceiling is orders of magnitude higher
  (~100K req/sec vs. ~1K for Postgres, as a stated assumption).
- **At very-high volume, one node is enough by throughput — but still run a small
  replicated cluster.** Reason: **availability**, not capacity.
  - QPS being under the ceiling does **not** prevent a crash — a single node can still go
    down from hardware failure, OOM, bad deploy, or an AZ outage, all independent of load.
  - If the only cache node dies, 100% of read traffic (not just the ~10% miss traffic)
    suddenly hits the DB replica layer, which was never sized for that.
- **Write-through on link creation** (to fix read-after-write, see §6) has a real cost:
  fills cache with links that may never be read again, increasing eviction pressure on
  genuinely popular content.
  - **Fix: short TTL** (e.g. 60s) on write-through entries — long enough to cover "user
    clicks their own fresh link immediately," short enough not to permanently compete for
    cache space.

## 5. Database

- **Reads never go to Master**, even though Master *could* technically serve them — the
  point is to protect Master's full capacity for writes, since writes have nowhere else to go.
- **Exception:** read-after-write consistency (see §6) — sometimes worth reading a user's
  own just-written data from Master or from a write-through cache, briefly, while general
  traffic still goes to replicas.
- **Master is kept at 1 far longer than anything else**, because scaling Master isn't free
  like scaling stateless/read-only components — multiple masters raise the question of what
  happens when two masters get a write to the same key at the same time (conflict
  resolution is a genuinely hard distributed-systems problem).
- **Escalation order when Master write volume becomes a real constraint:**
  1. Vertical scaling (bigger instance) — cheapest, no architecture change
  2. Sharding (partition keyspace across multiple masters, e.g. by hash of the short key) —
     each shard is still single-master for its own data, so you're avoiding the conflict
     problem, not solving it
  3. True multi-master with conflict resolution — rare, last resort

### Sharding specifics

- **Shard key candidate: the short key itself**, hashed — `hash(short_key) % num_shards`.
  Every record has one, it's close to uniformly random, and every read request already
  includes it (it's in the URL), so routing goes straight to the right shard.
- **Bad shard keys:** URL length (doesn't vary — all keys are fixed length, so it doesn't
  distribute anything), creation date or user ID (uneven distribution, and reads don't
  arrive with that info anyway).
- **Resizing gotcha:** with plain `% num_shards`, changing the shard count remaps almost
  *every* existing key, not just new ones — because the modulo result changes for nearly
  all keys when N changes. This forces a massive data migration.
  - **Fix: consistent hashing** — only ~1/N of keys move on a resize, not nearly all of them.

## 6. Write Path & Consistency

- **Order matters: write to Master first, then fan out to Redis/replicas — never the
  reverse.**
  - If Redis were written first and the Master write then failed, Redis would hold a link
    the database has no record of. It would work temporarily, then silently break (on
    eviction) with no corresponding "deletion" event anywhere — a hard bug to trace.
  - General principle: **write to the source of truth first, then propagate to anything
    that's just a performance optimization** (cache, search index, replicas).
- **Master → Read Replica replication is asynchronous.** Mark this arrow as visually
  distinct (dashed/labeled) from synchronous arrows in a diagram — it represents real lag,
  not an instant copy.
- **Read-after-write problem:** if a user creates a link and clicks it immediately, the
  replica may not have caught up yet → false "not found," even though the record exists.
  Fixed by write-through caching at creation (§4) or conditionally reading from Master for
  the user's own fresh write.

## 7. Load Balancer

- The standard `load / capacity` formula doesn't really apply — nothing sits upstream of
  the LB to filter traffic the way replicas/cache filter traffic for the DB.
- A single modern LB can often handle tens–hundreds of thousands of req/sec — usually not
  the bottleneck.
- **Reasons to run more than one, and neither is about raw throughput:**
  1. Availability/failover — a single LB is a single point of failure for the entire system
  2. Geographic distribution — one per region for latency, plus a global routing layer

## 8. Design Process (how to present it)

- **Don't start the diagram with Redis already in it.** Start with Client → LB → App Server
  → DB, hit the real bottleneck the numbers create, *then* introduce Redis as the fix for
  that named problem. Same for replicas, sharding, extra LBs — every component should enter
  because it solves a problem you just identified, not because it's "expected."
- **When numbers round to 1–2 of everything (as they do at medium volume), say so out
  loud** — "at this volume, a single instance handles it, no distributed complexity needed"
  is itself the correct architectural conclusion, not a non-answer.
- Reaching for a distributed system when the numbers don't justify it is the mirror-image
  mistake of under-designing — both are red flags.

## Worked example — very high volume (final numbers)

| Component | Count | Basis |
|---|---|---|
| App Servers | 156 | (77,000 + 770) peak QPS / 500 per server ≈ 155.5 → 156 |
| Redis | 1 primary + 2–3 replicas | Throughput needs 1; replicas are for availability |
| DB Replicas | 8 | 77,000 × (1 − 0.9) = 7,700 / 1,000 per-instance ceiling ≈ 7.7 → 8 |
| DB Master | 1 | 770 writes/sec is well within a single instance; escalate via vertical
  scaling → sharding → multi-master only if this changes |
| Load Balancers | 2 (+ optionally 1 more for rolling-deploy headroom) | 77,770 / 50,000 per-LB ≈ 1.56 → 2; extra is for availability, not load |

## Revision self-check questions

**Traffic numbers**
1. How do you go from monthly writes/reads to peak QPS? Say every step.
2. Why multiply by 2 for peak? Could 2x be wrong here?
3. What goes wrong if you size servers using average QPS instead of peak?

**Sizing any component**
4. What are the 3 steps you always follow to size any component?
5. For each of these, what traffic actually reaches it: App Server, Redis, DB Replica, DB Master?
6. Is cache hit rate calculated or assumed? Why does that matter?

**Redis**
7. Why can Redis handle so many more requests/sec than the database?
8. At very high volume, is one Redis node enough? When does that answer change?
9. If someone says "you're nowhere near capacity, how could it still go down?" — what's your answer?
10. What's the downside of writing every new link into Redis immediately? What's the fix?

**Database**
11. Why don't reads ever go to Master, even though it could technically serve them?
12. When is it okay to read from Master anyway?
13. Why do we try to keep Master at just 1, more than any other component?
14. If Master can't handle the writes anymore, what do you try first, second, last?
15. If sharding, what would you split by? Why?
16. If you add more shards later, what happens to existing data? What fixes that?

**Load Balancer**
17. Why doesn't "traffic ÷ capacity" really apply to load balancers?
18. What are the two real reasons to use more than one load balancer?

**Write flow**
19. Does it matter whether you write to the database or Redis first? What breaks if you pick wrong?
20. What does the arrow from Master to Replica mean, and why should it look different from other arrows?
21. What's the actual problem a user hits if a link doesn't show up right after creation?

**Design process**
22. Should Redis be in the diagram from the start, or only once you have a reason?
23. If your numbers all round to 1 or 2 of everything, what should you say instead of just showing the numbers?