import argparse, sys, json
from pathlib import Path
from ..core.config import load_config, DEFAULT_CONFIG
from ..core.measurement import MeasurementRunner
from ..core.analysis import analyze_run

def cmd_measure(args):
    try:
        cfg = load_config(args.config) if args.config else DEFAULT_CONFIG
    except Exception as e:
        print(f"Config load failed: {e}\nUsing defaults.")
        cfg = DEFAULT_CONFIG
    runner = MeasurementRunner(cfg)
    res = runner.run()
    print(json.dumps({"run_dir": res.run_dir, "success": res.success_map}, indent=2))

def cmd_analyze(args):
    res = analyze_run(args.parquet, poly_order=args.poly_order)
    out = Path(args.output or Path(args.parquet).parent / "analysis.json")
    out.write_text(json.dumps({
        "poly": res["poly"].tolist(),
        "ordered": res["ordered"],
        "resolution": {
            "lambda_nm": res["resolution"][0].tolist(),
            "fwhm_nm": res["resolution"][1].tolist()
        }
    }, indent=2))
    print(f"Wrote {out}")

def main():
    p = argparse.ArgumentParser("spectro")
    sub = p.add_subparsers(dest="cmd")

    m = sub.add_parser("measure", help="Run measurement per config")
    m.add_argument("--config", type=str, help="Path to SciLab.yaml")
    m.set_defaults(func=cmd_measure)

    a = sub.add_parser("analyze", help="Analyze a run parquet")
    a.add_argument("parquet", type=str, help="Path to frames.parquet")
    a.add_argument("--poly-order", type=int, default=3)
    a.add_argument("--output", type=str)
    a.set_defaults(func=cmd_analyze)

    args = p.parse_args()
    if not hasattr(args, "func"):
        p.print_help(); sys.exit(1)
    args.func(args)

if __name__ == "__main__":
    main()
