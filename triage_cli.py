"""CLI entrypoint for the AfyaPlus Triage Engine.

Implementation lives in triage/engine.py. Run:

    python triage_cli.py "My chest hurts and I cannot breathe properly"
"""

from triage.engine import main

if __name__ == "__main__":
    main()
