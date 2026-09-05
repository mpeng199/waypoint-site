"""Which guards never actually observed anything?

    python3 audit_guards.py

mutate.py asks whether the suite notices a break. This asks the other
question: is any guard asleep?

A check that loops over an empty list passes. So does one whose regex stopped
matching the markup it was written for. Both report success and neither has
looked at the site since the day it was written. This instruments ok() and
bad() to record which function called them, then names every check_ function
that finished without saying a single thing.
"""
import re, sys, inspect, collections
sys.path.insert(0, ".")
import check

seen = collections.Counter()

def record(orig):
    def wrapped(msg):
        # walk out to the nearest check_ frame: a guard with a nested helper
        # reports the helper's name otherwise, and looks silent
        f = next((fr.function for fr in inspect.stack()[1:]
                  if fr.function.startswith("check_")), inspect.stack()[1].function)
        seen[f] += 1
        return orig(msg)
    return wrapped

check.ok = record(check.ok)
check.bad = record(check.bad)

names = [n for n in dir(check) if n.startswith("check_")]
for n in names:
    fn = getattr(check, n)
    if not callable(fn):
        continue
    try:
        fn()
    except SystemExit:
        pass
    except Exception as e:
        print(f"  ERROR  {n}: {type(e).__name__}: {e}")

silent = [n for n in names if callable(getattr(check, n)) and not seen[n]]
print(f"\n{len(names)} guards, {len(silent)} of which observed nothing:\n")
if silent:
    print("  A guard that says nothing either loops over an empty list or has\n"
          "  a pattern that stopped matching. Both pass. Neither has looked at\n"
          "  the site since the day it was written.\n")
for n in sorted(silent):
    doc = (getattr(check, n).__doc__ or "").strip().split("\n")[0]
    print(f"  {n:52} {doc[:70]}")
print()
print("  --- the ten guards that observe the least ---")
for n in sorted(names, key=lambda x: seen[x])[:14]:
    if callable(getattr(check, n)):
        print(f"  {seen[n]:5}  {n}")
