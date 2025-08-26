#!/usr/bin/env python3
import csv, sys, argparse, os
from idlelib.iomenu import errors


def read_trace(filename, debug=False):
    times = []
    levels = []
    with open(filename, newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or row[0].startswith("Time"):
                continue
            t = float(row[0])
            v = int(row[1])
            times.append(t)
            levels.append(v)

    # Extract transitions
    transitions = [(times[0], levels[0])]
    for t, v in zip(times[1:], levels[1:]):
        if v != transitions[-1][1]:
            transitions.append((t, v))

    # Compute run lengths
    runs = []
    for i in range(len(transitions) - 1):
        t0, v0 = transitions[i]
        t1, _ = transitions[i + 1]
        runs.append((v0, t1 - t0))
    runs.append((transitions[-1][1], times[-1] - transitions[-1][0]))

    if debug:
        print("Runs: [" + ", ".join(f"({x}, {y * 1000:.2f} ms)" for x, y in runs) + "]")

    return runs, times, levels


def build_bitvector(runs, debug=False):
    # Estimate base quantum (shortest low pulse)
    low_durations = [dur for val, dur in runs if val == 0]
    T0 = min(low_durations) if low_durations else min(d for _, d in runs)
    if debug:
        print(f"Estimated T0 = {T0 * 1000:.3f} ms")

    # Trim to first idle ≥ 20×T0
    for i, (val, dur) in enumerate(runs):
        if dur >= 20 * T0:
            if debug:
                print(f"Trimming to start at run {i + 1} (val={val}, dur={dur * 1000:.3f} ms)")
            runs = runs[i + 1:]
            break

    # Build bitvector
    bitvec = []
    for val, dur in runs:
        n = round(dur / T0)
        bitvec.extend([val] * n)

    whole_bitvector = ''.join(str(b) for b in bitvec)
    if debug:
        print(f"Bitvector ({len(bitvec)} bits):\n{whole_bitvector}")
    return whole_bitvector, T0


def extract_and_verify(bitvec: str, min_idle=20, debug=False):
    frames = []
    positions = []
    i = 0
    n = len(bitvec)

    while i < n:
        if bitvec[i] == '0':
            start = i
            while i < n:
                if bitvec[i] == '1':
                    run_start = i
                    while i < n and bitvec[i] == '1':
                        i += 1
                    run_len = i - run_start
                    if run_len >= min_idle:
                        end = run_start
                        frames.append(bitvec[start:end])
                        positions.append((start, end))
                        break
                else:
                    i += 1
        else:
            i += 1

    if not frames:
        raise ValueError("No frames found")

    print(f"Frames found: {len(frames)}")
    first = frames[0]
    # Verify all frames identical
    errors = 0
    for idx, f in enumerate(frames[1:], start=1):
        if f != first:
            print(f"Frame {idx} differs")
            errors += 1

    if errors > 0:
        debug_print_frame_and_bitvec(first, bitvec, positions)
        raise ValueError(f"{errors} frames differ, unreliable capture")

    return first, len(frames) - errors, positions


def debug_print_frame_and_bitvec(frame: str, bitvec: str, positions: list[int]):
    print("\n=== Extracted Frame ===")
    print(frame)
    print("=======================\n")

    frame_len = len(frame)

    print("=== Bitvector with frames aligned ===")
    for start, _ in positions:
        line = bitvec[start:start + frame_len]
        # Show an indicator if this line differs from the reference frame
        marker = "OK" if line == frame else "DIFF"
        print(f"{line}   {marker}")
    print("=======================\n")


def whole_line(bitvec, start, end, width=80):
    """Break long bitvector lines nicely with highlighting window."""
    left = max(0, start - 5)
    right = min(len(bitvec), end + 5)
    snippet = bitvec[left:right]
    prefix = "..." if left > 0 else ""
    suffix = "..." if right < len(bitvec) else ""
    return prefix + snippet + suffix


def main():
    parser = argparse.ArgumentParser(description="Extract repeated bitvector frame from Saleae CSV trace.")
    parser.add_argument("traces", nargs="+", help="Input CSV trace file(s)")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("--outdir", "-o", help="Output directory for .frame files", default=None)
    args = parser.parse_args()

    trace_errors = []
    for trace in args.traces:
        print(f"\nProcessing {trace}...")

        runs, _, _ = read_trace(trace, debug=args.debug)
        whole_bitvector, T0 = build_bitvector(runs, debug=args.debug)
        try:
            frame, count, positions = extract_and_verify(whole_bitvector, debug=args.debug)
            if 30 > len(frame) or len(frame) > 34:
                raise ValueError(
                    f"Frame too {'short' if len(frame) < 3 else 'long'} ({len(frame)} bits), unreliable capture")
        except ValueError as e:
            print(f"Error processing {trace}: {e}")
            trace_errors.append((trace, frame, str(e)))
            continue

        print(f"Frame (length {len(frame)}): {frame} found {count} times")

        if count >= 5:
            if args.outdir:
                os.makedirs(args.outdir, exist_ok=True)
                outname = os.path.join(
                    args.outdir, os.path.basename(trace).rsplit('.', 1)[0] + ".frame"
                )
            else:
                outname = trace.rsplit('.', 1)[0] + ".frame"

            with open(outname, "w") as f:
                f.write(frame + "\n")

            if args.debug:
                print(f"Frame written to {outname}")
        else:
            if args.debug:
                print(f"Skipping {trace}, frame did not repeat enough times.")

    if trace_errors:
        print("\n==== Errors ====")
        for trace, frame, err in trace_errors:
            print(f"{trace}: {err} \t Frame: {frame}")


if __name__ == "__main__":
    main()
