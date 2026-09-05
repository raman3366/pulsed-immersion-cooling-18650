import sys, time
now = time.time()
L1 = ["square_smoke","steady_f0.00_A0.00_Q1_C3","steady_f0.00_A0.00_Q2_C3"] + [f"sine_f{f}_A{a}_Q2_C3" for f in ("0.10","0.25","0.50") for a in ("0.20","0.40","0.60")] + [f"square_f1.00_D{d}_Q2_C3" for d in ("0.25","0.50","0.75")] + ["fields_sine_f0.10_A0.60_Q2_C3"]
L2 = [f"steady_f0.00_A0.00_Q{q}_C3" for q in (3,4,5)] + [f"sine_f{f}_A{a}_Q2_C3" for f in ("1.00","2.00") for a in ("0.20","0.40","0.60")] + [f"square_f0.50_D{d}_Q2_C3" for d in ("0.25","0.50","0.75")] + ["fields_sine_f2.00_A0.60_Q2_C3", "fields_steady_f0.00_A0.00_Q2_C3"]
HRS = {"square_smoke":0.4,"steady_f0.00_A0.00_Q4_C3":5.5,"steady_f0.00_A0.00_Q5_C3":6.7,
       "fields_sine_f0.10_A0.60_Q2_C3":5.0,"fields_sine_f2.00_A0.60_Q2_C3":5.0, "fields_steady_f0.00_A0.00_Q2_C3":4.8}
END = {"square_smoke":20.0,"fields_sine_f0.10_A0.60_Q2_C3":870.0,"fields_sine_f2.00_A0.60_Q2_C3":870.0}
state = {}
for ln in sys.stdin.read().split("\n"):
    p = ln.split()
    if len(p) == 3: state[p[0]] = (p[1], p[2])
if len(state) < len(L1) + len(L2):
    print(f"INCOMPLETE DATA ({len(state)}/{len(L1)+len(L2)} case rows) — network glitch, ignore this tick")
    sys.exit(3)
def render(lane, name):
    t_free = now; out = [f"--- {name}"]
    for c in lane:
        t, end = state.get(c, ("-","-")); dur = HRS.get(c, 4.7)*3600; tend = END.get(c, 900.0)
        if c == "steady_f0.00_A0.00_Q2_C3":
            out.append(f"  {c:34s} 100%  DONE (baseline = bwd_dt0.0125_Q2)"); continue
        if end == "1":
            out.append(f"  {c:34s} 100%  DONE"); continue
        if t not in ("-",""):
            frac = float(t)/tend
            rem = dur*(1-frac); eta = time.strftime("%a %H:%M", time.localtime(now+rem))
            out.append(f"  {c:34s} {frac*100:4.0f}%  RUNNING  eta {eta}"); t_free = now + rem
        else:
            eta = time.strftime("%a %H:%M", time.localtime(t_free+dur))
            out.append(f"  {c:34s}    0%  queued   eta {eta}"); t_free += dur
    return out, t_free
o1, f1 = render(L1, "lane 1"); o2, f2 = render(L2, "lane 2")
print("\n".join(o1)); print("\n".join(o2))
done = sum(1 for c in L1+L2 if state.get(c,("-","-"))[1]=="1" or c=="steady_f0.00_A0.00_Q2_C3")
print(f"--- overall: {done}/{len(L1+L2)} cases done ({done/len(L1+L2)*100:.0f}%); BLOCK3_DONE eta ~ {time.strftime('%a %H:%M', time.localtime(max(f1,f2)))}")
